import csv
import math
import os
import traceback
from copy import deepcopy

from ..cache import CACHE_VALUES
from ..classes import (
    InputUTXO,
    PaymentDetail,
    PaymentGroup,
    PreparationDetail,
    TransactionPlan,
)
from ..constants.commands import (
    CREATE_FILE_COPY_TO_DOCKER,
    DELETE_FILE,
    DUST_SUBMIT_FUNCTION_CALL,
    DUST_TX_SUBMIT_SCRIPT,
    FIND_PYTHON_FUNCTION,
    GROUP_TX_ONGOING_FUNCTION_CALL,
    GROUP_TX_ONGOING_SET_FUNCTION_SCRIPT,
    LATEST_SLOT_NUMBER_BASH_FUNCTION,
    POST_PREP_TX_SUBMIT_SCRIPT,
    QUERY_TIP,
    QUERY_WALLET_UTXO_NO_FILE,
    QUERY_WALLET_UTXO_VIA_TXID,
    STATUS_MESSAGE_SETUP,
    TRANSACTION_FEE,
    TRANSACTION_SIGN,
    TRANSACTION_SUBMIT,
    TRANSACTION_TXID,
    TX_STATUS_SCRIPT,
    UPDATE_TRANSACTION_PLAN_FILE,
)
from ..constants.common import (
    CardanoNetwork,
    DustCollectionMethod,
    ScriptMethod,
    TransactionStatus,
)
from ..constants.exceptions import (
    EmptyList,
    InsufficientBalance,
    InvalidFileError,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from .cli_utils import (
    check_and_create_temp_directory,
    create_transaction_command,
    create_transaction_file,
    delete_temp_file,
    get_latest_slot_number,
    get_protocol_parameters,
    get_stake_address_balance,
    get_staking_address,
    get_total_amount_plus_fee,
    get_transaction_byte_size,
    get_transaction_fee,
    get_tx_size,
    get_wallet_utxo,
    sign_tx_file,
)
from .common import get_script_settings, print_to_console


def parse_sources_csv_file(filename):
    """
    Parse a source CSV File and returns a map of address + signing key file details
    :param filename: filename of the source csv file
    :return: map of address + signing key file details
    """
    source_details = {}
    with open(filename, "r") as source_file:
        csv_reader = csv.reader(source_file)
        for source_detail in csv_reader:
            address = source_detail[0].strip()
            source_details[address] = [sk_file.strip() for sk_file in source_detail[1:]]
            if len(source_details[address]) < 1:
                raise EmptyList(field="Witness List")
    if len(source_details) == 0:
        raise EmptyList(field="Witness List")
    return source_details


def parse_payment_utxo_file(filename):
    """
    Parse a payment CSV file and returns a list of utxo details (address + amount)
    :param filename: filename of the payment utxo csv file
    :return: list of utxo details (address + amount)
    """
    utxo_details = []
    with open(filename, "r") as utxo_file:
        csv_reader = csv.reader(utxo_file)
        for utxo_detail_list in csv_reader:
            utxo_details.append(
                PaymentDetail(
                    address=utxo_detail_list[0].strip(),
                    amount=int(utxo_detail_list[1]),
                ),
            )
    if len(utxo_details) == 0:
        raise EmptyList(field="Output UTxO List")
    return utxo_details


def group_output_utxo(
    output_list,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Initially Group a list of output utxo details based on the protocol parameters and transaction sizes
    :param output_list: utxo output list to be grouped
    :param network: Network where the function will get the minimum transaction fee
    :param method: Method that will be used for creating transaction draft
    :param reward_details: Map containing source stake rewards
    :return: Initial Groupings List of Output UTxO details
    """
    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)
    if not isinstance(output_list, list):
        raise InvalidType(type=type(output_list), message="Invalid output list type.")

    # Get Protocol Parameters
    try:
        protocol_details = get_protocol_parameters(network=network, method=method)
        max_tx_size = protocol_details.get("max_tx_size")
    except ScriptError as e:
        raise e
    except Exception as e:
        raise ScriptError(
            message="Unexpected Error Getting Protocol Parameters.",
            error=e,
            traceback=traceback.format_exc(),
        )  # Error during protocol parameter fetch

    # Get Initial Transaction Byte Size
    num_output = len(output_list)
    try:
        initial_tx_size = get_transaction_byte_size(
            input_arg=1,
            output_arg=output_list,
            method=method,
            network=network,
        )
    except ScriptError as e:
        raise e
    except Exception as e:
        raise ScriptError(
            message="Unexpected Error Getting TX Byte Size.",
            error=e,
            traceback=traceback.format_exc(),
        )  # Error during Initial Transaction Byte Size Fetch

    if initial_tx_size < max_tx_size:
        return [output_list]

    bin_index = math.floor(num_output * max_tx_size / initial_tx_size)
    max_tx_per_group_count = 0
    while bin_index > 0:
        tx_size = get_transaction_byte_size(
            input_arg=1,
            output_arg=output_list[: max_tx_per_group_count + bin_index],
            method=method,
        )
        if tx_size > max_tx_size:
            # Fail
            bin_index = math.floor(bin_index / 2)
        else:
            # Success
            max_tx_per_group_count += bin_index

    # Group Output UTxOs
    utxo_groups = []
    index = 0
    while index < num_output:
        end_index = index + max_tx_per_group_count
        utxo_groups.append(output_list[index:end_index])
        index = end_index

    return utxo_groups


def preparation_step(
    source_address,
    source_details,
    payments_utxo_file,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    include_rewards=False,
):
    """
    Prepare and create an initial input utxo transaction
    :param source_address: source address
    :param source_details: source details map (address + signing key file)
    :param payments_utxo_file: csv file containing payment utxo details
    :param network: Network where the function will get the cardano details
    :param method: Method that will be used for creating initial input transaction
    :param include_rewards: Flag on whether to include getting the stake rewards
    :return: initial groups + initial transaction details
    """
    if not isinstance(source_address, str):
        raise InvalidType(
            type=type(source_address),
            message="Invalid source address type.",
        )
    if not isinstance(source_details, dict):
        raise InvalidType(
            type=type(source_details),
            message="Invalid source details type.",
        )
    if not isinstance(payments_utxo_file, str):
        raise InvalidType(
            type=type(payments_utxo_file),
            message="Invalid payments UTxO file type.",
        )
    if not isinstance(include_rewards, bool):
        raise InvalidType(
            type=type(include_rewards),
            message="Invalid include rewards type.",
        )

    # Parse File
    try:
        output_list = parse_payment_utxo_file(filename=payments_utxo_file)
    except ScriptError as e:
        raise e
    except Exception as e:
        raise InvalidFileError(
            file=payments_utxo_file,
            message="Unexpected Error Parsing UTxO File.",
            error=e,
            traceback=traceback.format_exc(),
        )  # Error during output file parsing

    # Get wallet utxos
    try:
        wallet_utxo_details = []
        for address in source_details:
            wallet_utxo_details += get_wallet_utxo(
                address=address,
                network=network,
                method=method,
            )
    except ScriptError as e:
        raise e
    except Exception as e:
        raise ScriptError(
            message="Unexpected Error Fetching Wallet UTxO.",
            error=e,
            traceback=traceback.format_exc(),
            additional_context={"address": address},
        )  # Error during wallet utxo fetch

    # Include Rewards
    stake_reward_details = {}
    if include_rewards:
        stake_address = get_staking_address(
            full_address=source_address,
            network=network,
            method=method,
        )
        stake_balance = get_stake_address_balance(
            stake_address=stake_address,
            network=network,
            method=method,
        )
        stake_reward_details = {
            "stake_address": stake_address,
            "stake_amount": stake_balance,
        }

    # Create Initial Output Group List
    try:
        output_group_list = group_output_utxo(
            output_list=output_list,
            network=network,
            method=method,
        )
    except ScriptError as e:
        raise e
    except Exception as e:
        raise ScriptError(
            message="Unexpected Error Grouping Output UTxOs.",
            error=e,
            traceback=traceback.format_exc(),
        )  # Error during output group list generation

    # Get total amount of output groups
    total_output_amount_list = []
    output_group_details = []
    group_index = 0
    for output_group in output_group_list:
        try:
            total_amount, total_fee = get_total_amount_plus_fee(
                input_arg=1,
                output_list=output_group,
                network=network,
                method=method,
            )
            total_amount_plus_fee = total_amount + total_fee
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Getting Total Amount and Fee.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error in total computation
        total_output_amount_list.append(total_amount_plus_fee)
        output_group_details.append(
            PaymentGroup(
                payment_details=output_group,
                amount=total_amount,
                fee=total_fee,
                index=group_index,
            ),
        )
        group_index += 1
    total_output_amount = sum(total_output_amount_list)

    # Get total amount in utxo wallet
    total_input_amount = 0
    for utxo_detail in wallet_utxo_details:
        total_input_amount += utxo_detail.amount

    # Add rewards
    total_input_amount += stake_reward_details.get("stake_amount", 0)

    if total_input_amount < total_output_amount:
        raise InsufficientBalance(
            required_amount=total_output_amount,
            current_amount=total_input_amount,
        )

    # Sort input utxos based on amount
    wallet_utxo_details.sort(key=lambda ua: ua.amount, reverse=True)

    # Get input utxos to use based on total_amount
    input_utxos = []
    input_arg_amount = 0
    input_utxo_index = 0
    while input_arg_amount < total_output_amount and input_utxo_index < len(
        wallet_utxo_details,
    ):
        utxo_detail = wallet_utxo_details[input_utxo_index]
        input_utxos.append(utxo_detail)
        input_arg_amount += utxo_detail.amount
        input_utxo_index += 1

    # Create output utxo argument list
    output_arg_list = []
    if len(output_group_list) == 1:
        output_arg_list = output_group_list[0]
    else:
        for amount in total_output_amount_list:
            output_arg_list.append(PaymentDetail(address=source_address, amount=amount))

    # Create Input Draft Unsigned Transaction
    try:
        transaction_draft_file = create_transaction_file(
            input_arg=input_utxos,
            output_arg=output_arg_list,
            method=method,
        )
    except ScriptError as e:
        raise e
    except Exception as e:
        raise ScriptError(
            message="Unexpected Error Creating TX Draft.",
            error=e,
            traceback=traceback.format_exc(),
        )  # Error on transaction draft creation

    # Get max tx size
    try:
        protocol_details = get_protocol_parameters(network=network, method=method)
        max_tx_size = protocol_details.get("max_tx_size")
    except ScriptError as e:
        raise e
    except Exception as e:
        raise ScriptError(
            message="Unexpected Error Fetching Protocol Parameters.",
            error=e,
            traceback=traceback.format_exc(),
        )  # Error during protocol parameter fetch

    tx_size = get_tx_size(tx_file=transaction_draft_file, method=method)

    return {
        "output_details": output_group_details,
        "wallet_utxos": wallet_utxo_details,
        "transaction_filename": transaction_draft_file,
        "max_tx_size": max_tx_size,
        "require_dust_collection": tx_size > max_tx_size,
        "stake_reward_details": stake_reward_details,
    }


def dust_collect(
    input_utxos,
    transaction_draft_filename,
    max_tx_size,
    source_address,
    source_details,
    payment_group_details=[],
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE,
    dust_collection_threshold=10000000,
    reward_details={},
):
    """
    Create an updated tx Draft with dust collected utxos
    :param input_utxos: Input UTxO detail list that will be check for dust collection
    :param payment_group_details: Payment Group Details List
    :param transaction_draft_filename: Initial Preparation TX Draft File
    :param max_tx_size: Maximum Transaction Size
    :param source_address: Source Address
    :param source_details: Source Details
    :param network: Network that will be used to connect for dust collection
    :param method: Method that will be used for creating the tx files
    :param dust_collection_method: Dust collection method used (Where will the dust utxos be placed)
    :param dust_collection_threshold: Basis amount for dust collection
    :param reward_details: Map containing source stake rewards
    :return: Updated init details
    """

    if not isinstance(input_utxos, list):
        raise InvalidType(
            type=type(input_utxos),
            message="Invalid Input UTXO List Type.",
        )
    if not isinstance(transaction_draft_filename, (str, dict)):
        raise InvalidType(
            type=type(transaction_draft_filename),
            message="Invalid Transaction Draft Filename Type.",
        )
    if not isinstance(max_tx_size, int):
        raise InvalidType(
            type=type(max_tx_size),
            message="Invalid Max Transaction Size Type.",
        )
    if not isinstance(source_address, str):
        raise InvalidType(
            type=type(source_address),
            message="Invalid Source Address Type.",
        )
    if not isinstance(source_details, dict):
        raise InvalidType(
            type=type(source_details),
            message="Invalid Source Details Type.",
        )
    if not isinstance(dust_collection_threshold, int):
        raise InvalidType(
            type=type(dust_collection_threshold),
            message="Invalid Dust Threshold Type.",
        )
    if dust_collection_method not in [dcm for dcm in DustCollectionMethod]:
        raise InvalidType(
            type=type(dust_collection_method),
            message="Invalid Dust Collection Method Type.",
        )
    if not isinstance(reward_details, dict):
        raise InvalidType(
            type=type(reward_details),
            message="Invalid Reward Details Type.",
        )
    if network not in [cn for cn in CardanoNetwork]:
        raise InvalidNetwork(network=network)
    if method not in [sm for sm in ScriptMethod]:
        raise InvalidMethod(method=method)

    print_to_console(
        message="Creating Dust Collected UTxOs...",
        output_format=CACHE_VALUES.get("output_format"),
    )
    new_wallet_utxos = []
    dust_utxos = []
    for utxo_detail in input_utxos:
        if utxo_detail.amount < dust_collection_threshold:
            dust_utxos.append(utxo_detail)
        else:
            new_wallet_utxos.append(utxo_detail)

    # Create mock transaction dust collected utxos
    dust_utxos.sort(key=lambda du: du.amount, reverse=True)
    dust_utxo_groups = {}
    if dust_collection_method == DustCollectionMethod.COLLECT_TO_SOURCE:
        dust_utxo_groups[source_address] = dust_utxos
    else:
        for utxo_detail in dust_utxos:
            dust_address = utxo_detail.address
            if dust_utxo_groups.get(dust_address) is None:
                dust_utxo_groups[dust_address] = []
            dust_utxo_groups[dust_address].append(utxo_detail)

    signing_key_files = []
    for address in source_details:
        signing_key_files += source_details[address]
    signing_key_files = list(set(signing_key_files))

    final_dust_group_details = {}

    # Create Final Dust Groups
    for target_address in dust_utxo_groups:
        dust_utxo_list = dust_utxo_groups[target_address]
        final_address_dust_group = []
        temp_index = len(dust_utxo_list)
        dust_start_index = 0
        dust_input_index = 0
        dust_payment_output = []
        input_dust_list = []
        while dust_start_index < len(dust_utxo_list):
            if temp_index == 0:
                final_address_dust_group.append(
                    PreparationDetail(
                        prep_input=input_dust_list,
                        prep_output=dust_payment_output,
                    ),
                )
                dust_start_index += dust_input_index
                temp_index = len(dust_utxo_list)
                dust_input_index = 0
                dust_payment_output = []
                input_dust_list = []
                continue

            temp_end_index = dust_start_index + dust_input_index + temp_index
            temp_dust_inputs = dust_utxo_list[dust_start_index:temp_end_index]

            if final_address_dust_group:
                # A dust collected utxo created and will be used on the succeeding groups
                temp_dust_inputs.append(
                    InputUTXO(
                        address=final_address_dust_group[-1].prep_output[0].address,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=final_address_dust_group[-1].prep_output[0].amount,
                        dust_collected_utxo=True,
                    ),
                )

            temp_input_total = sum(
                [temp_input_dust.amount for temp_input_dust in temp_dust_inputs],
            )
            temp_input_num_witness = set()
            for input_utxo in temp_dust_inputs:
                temp_input_num_witness.add(input_utxo.address)
            temp_signing_key_files = []
            for address in temp_input_num_witness:
                temp_signing_key_files += source_details[address]
            temp_signing_key_files = list(set(temp_signing_key_files))

            temp_draft_file = None
            if method == ScriptMethod.METHOD_PYCARDANO:
                # Create a temporary draft file
                temp_draft_file = create_transaction_file(
                    input_arg=temp_dust_inputs,
                    output_arg=[
                        PaymentDetail(address=target_address, amount=temp_input_total),
                    ],
                    method=method,
                )
                temp_draft_file = sign_tx_file(
                    tx_file=temp_draft_file,
                    signing_key_files=signing_key_files,
                    method=method,
                    network=network,
                )

            temp_input_fee = get_transaction_fee(
                len(temp_dust_inputs),
                1,
                num_witness=len(temp_signing_key_files),
                draft_file=temp_draft_file,
                network=network,
                method=method,
            )
            temp_dust_amount = temp_input_total - temp_input_fee
            temp_dust_payment_output = [
                PaymentDetail(address=target_address, amount=temp_dust_amount),
            ]

            tx_size = get_transaction_byte_size(
                input_arg=temp_dust_inputs,
                output_arg=temp_dust_payment_output,
                method=method,
                network=network,
                signing_key_files=temp_signing_key_files,
            )
            if tx_size >= max_tx_size:
                # Fail
                temp_index = math.floor(temp_index / 2)
            else:
                # Success
                input_dust_list = temp_dust_inputs
                dust_payment_output = temp_dust_payment_output
                dust_input_index += temp_index
            if dust_input_index > len(dust_utxo_list):
                temp_index = 0
        final_dust_group_details[target_address] = final_address_dust_group

    for address in final_dust_group_details:
        dust_groups = final_dust_group_details[address]
        # Create an input utxo basing on the last final dust group detail
        new_wallet_utxos.append(
            InputUTXO(
                address=dust_groups[-1].prep_output[0].address,
                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                tx_index=0,
                amount=dust_groups[-1].prep_output[0].amount,
                dust_collected_utxo=True,
            ),
        )

    new_wallet_utxos.sort(key=lambda ua: ua.amount, reverse=True)

    return {
        "output_details": payment_group_details,
        "dust_group_details": final_dust_group_details,
        "wallet_utxos": new_wallet_utxos,
        "transaction_filename": transaction_draft_filename,
        "max_tx_size": max_tx_size,
        "stake_reward_details": reward_details,
    }


def adjust_utxos(
    output_utxo_details,
    input_utxo_list,
    prep_tx_file,
    source_address,
    max_tx_size,
    reward_details={},
    allow_ttl_slots=100,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Adjustment step for the input and output utxos
    :param output_utxo_details: List of Output UTxO Group Details (Group List + Total Amount + Fee)
    :param input_utxo_list: List of Initial Transaction Input UTxO
    :param prep_tx_file: Filename of the preparation Tx draft file
    :param source_address: Source Address
    :param max_tx_size: Maximum Transaction Size
    :param reward_details: Map containing source stake rewards (Default: {})
    :param allow_ttl_slots: Maximum Allowable TTL slots for the transactions (Default: 100)
    :param network: Network where the function will get the cardano details
    :param method: Method that will be used for creating transaction drafts + fetching cardano details
    :return: Adjusted group details (preparation list + group list)
    """
    # Get settings
    masspayments_settings = get_script_settings()

    if not isinstance(output_utxo_details, list):
        raise InvalidType(
            type=type(output_utxo_details),
            message="Invalid Output UTxO Details List Type.",
        )
    if not isinstance(input_utxo_list, list):
        raise InvalidType(
            type=type(input_utxo_list),
            message="Invalid Input UTxO Details List Type.",
        )
    if not isinstance(source_address, str):
        raise InvalidType(
            type=type(source_address),
            message="Invalid Source Address Type.",
        )
    if not isinstance(max_tx_size, int):
        raise InvalidType(
            type=type(max_tx_size),
            message="Invalid Max Transaction Size Type.",
        )
    if not isinstance(allow_ttl_slots, int):
        raise InvalidType(
            type=type(allow_ttl_slots),
            message="Invalid Allow TTL Slots Type.",
        )
    if not isinstance(reward_details, dict):
        raise InvalidType(
            type=type(reward_details),
            message="Invalid Reward Details Type.",
        )
    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    # Group output groups
    over_max_group = []
    under_max_group = []
    temp_utxo_list = []

    if len(output_utxo_details) == 1:
        # Skip the steps and possibly include it in the prep stage
        utxo_details_list = output_utxo_details[0].payment_details or []
        # Add them to temp utxo list
        while len(utxo_details_list) > 0:
            temp_utxo_list.append(utxo_details_list.pop(0))

    for o_group_detail in output_utxo_details:
        # ttl = get_latest_slot_number(network=network, method=method) + allow_ttl_slots
        output_group_utxo_list = o_group_detail.payment_details
        if len(output_group_utxo_list) == 0:
            continue
        tx_size = get_transaction_byte_size(
            input_arg=1,
            output_arg=output_group_utxo_list,
            method=method,
            network=network,
        )
        o_group_detail.tx_size = tx_size
        if tx_size > max_tx_size:
            over_max_group.append(o_group_detail)
        else:
            under_max_group.append(o_group_detail)

    # Move extra utxos in a temporary group
    for o_group_detail in over_max_group:
        tx_size = o_group_detail.tx_size
        o_group_list = o_group_detail.payment_details
        group_amount = o_group_detail.amount
        group_fee = o_group_detail.fee
        while tx_size > max_tx_size:
            temp_utxo_list.append(o_group_list.pop(0))
            group_amount, group_fee = get_total_amount_plus_fee(
                input_arg=1,
                output_list=o_group_list,
                network=network,
                method=method,
            )
            tx_size = get_transaction_byte_size(
                input_arg=1,
                output_arg=o_group_list,
                method=method,
                network=network,
            )
        o_group_detail.tx_size = tx_size
        o_group_detail.amount = group_amount
        o_group_detail.fee = group_fee

    # Sort temp utxo list by amount
    temp_utxo_list.sort(key=lambda tu: tu.amount, reverse=True)

    # Add temp utxos in undersized group
    for u_group_detail in under_max_group:
        u_group_list = u_group_detail.payment_details
        tx_size = u_group_detail.tx_size
        group_amount = u_group_detail.amount
        group_fee = u_group_detail.fee
        temp_utxo_index = 0
        while temp_utxo_index < len(temp_utxo_list):
            next_index = temp_utxo_index + 1
            temp_u_group_list = (
                u_group_list + temp_utxo_list[temp_utxo_index:next_index]
            )
            group_amount, group_fee = get_total_amount_plus_fee(
                input_arg=1,
                output_list=temp_u_group_list,
                network=network,
                method=method,
            )
            tx_size = get_transaction_byte_size(
                input_arg=1,
                output_arg=temp_u_group_list,
                method=method,
                network=network,
            )
            if tx_size <= max_tx_size:
                # Add to group list
                u_group_list.append(temp_utxo_list.pop(temp_utxo_index))
            else:
                # Skip and continue with the next temp utxo
                temp_utxo_index += 1
        u_group_detail.tx_size = tx_size
        u_group_detail.amount = group_amount
        u_group_detail.fee = group_fee

    # Delete preparation transaction file
    try:
        delete_temp_file(filename=prep_tx_file, method=method)
    except ScriptError as e:
        raise e
    except Exception as e:
        raise InvalidFileError(
            message="Unexpected Error Deleting Prep TX File.",
            error=e,
            traceback=traceback.format_exc(),
            file=prep_tx_file,
        )  # Error during delete transaction draft file

    # Test adding temp utxos in prep transaction
    final_group_list = over_max_group + under_max_group
    final_group_list.sort(key=lambda utxo_group: utxo_group.index)

    # Create new prep utxo list
    prep_utxo_detail_list = []
    for utxo_group in final_group_list:
        prep_utxo_detail_list.append(
            PaymentDetail(
                address=source_address,
                amount=utxo_group.amount + utxo_group.fee,
            ),
        )

    # Test on prep utxo
    temp_utxo_index = len(temp_utxo_list)
    final_prep_list = deepcopy(prep_utxo_detail_list)
    final_input_list = []
    extra_group_details = PaymentGroup(index=len(prep_utxo_detail_list))
    initial_round = True
    while (temp_utxo_index > 0 and len(temp_utxo_list) > 0) or initial_round:
        initial_round = False
        temp_prep_list = final_prep_list + temp_utxo_list[0:temp_utxo_index]

        # Extra group for remaining temp_utxos
        extra_group = temp_utxo_list[temp_utxo_index:]
        e_amount = 0
        e_fee = 0
        e_tx_size = 0
        if len(extra_group) > 0:
            e_tx_size = get_transaction_byte_size(
                input_arg=1,
                output_arg=temp_prep_list,
                method=method,
                network=network,
            )
            e_amount, e_fee = get_total_amount_plus_fee(
                input_arg=1,
                output_list=extra_group,
                network=network,
                method=method,
            )
            temp_prep_list.insert(
                len(prep_utxo_detail_list),
                PaymentDetail(address=source_address, amount=e_amount + e_fee),
            )  # Add alongside the group utxos

        initial_check = True
        temp_input_utxos = []
        last_input_length = 0
        add_change_to_fee = False
        while True:
            # Get new total and fee
            input_arg = 1 if initial_check else temp_input_utxos
            temp_o_total, temp_o_fee = get_total_amount_plus_fee(
                input_arg=input_arg,
                output_list=temp_prep_list,
                network=network,
                method=method,
            )
            temp_o_tfee = temp_o_total + temp_o_fee

            # Get temp input utxo list
            temp_input_utxos = []
            temp_input_amt = 0
            temp_input_index = 0
            input_total = sum([input_utxo.amount for input_utxo in input_utxo_list])

            # Add rewards
            input_total += reward_details.get("stake_amount", 0)

            change_amount = input_total - temp_o_tfee
            if input_total < temp_o_tfee:
                raise InsufficientBalance(
                    required_amount=temp_o_tfee,
                    current_amount=input_total,
                )
            elif change_amount > masspayments_settings.cardano_minimum_amount:
                temp_o_required_amt = (
                    temp_o_tfee + masspayments_settings.cardano_minimum_amount
                )
            else:
                temp_o_fee += change_amount
                temp_o_tfee = temp_o_total + temp_o_fee
                temp_o_required_amt = temp_o_tfee

            while temp_input_amt < temp_o_required_amt and temp_input_index < len(
                input_utxo_list,
            ):
                utxo_detail = input_utxo_list[temp_input_index]
                temp_input_utxos.append(utxo_detail)
                temp_input_amt += utxo_detail.amount
                temp_input_index += 1

            if len(temp_input_utxos) == last_input_length:
                if change_amount < masspayments_settings.cardano_minimum_amount:
                    add_change_to_fee = True
                    print_to_console(
                        message=f"Change amounting to {change_amount} Lovelace will be added to fee. Fee is now "
                        f"{temp_o_fee} Lovelace",
                        output_format=CACHE_VALUES.get("output_format"),
                    )
                break
            else:
                last_input_length = len(temp_input_utxos)
                initial_check = False

            # Get transaction byte size
            tmp_size = get_transaction_byte_size(
                input_arg=temp_input_utxos,
                output_arg=temp_prep_list,
                reward_details=reward_details,
                method=method,
                network=network,
            )

        # Add utxo if it still fits in the transaction
        if tmp_size > max_tx_size:
            temp_utxo_index = math.floor(temp_utxo_index / 2)
        else:
            final_prep_list = temp_prep_list
            final_input_list = temp_input_utxos
            extra_group_details.payment_details = extra_group
            extra_group_details.amount = e_amount
            extra_group_details.fee = e_fee
            extra_group_details.index = len(prep_utxo_detail_list)
            extra_group_details.tx_size = e_tx_size
            temp_utxo_list = extra_group

    if len(extra_group_details.payment_details or []) > 0:
        # Add extra group in final_group_list
        final_group_list.append(extra_group_details)
        final_prep_list.insert(
            extra_group_details.index or len(prep_utxo_detail_list),
            PaymentDetail(
                address=source_address,
                amount=extra_group_details.amount + extra_group_details.fee,
            ),
        )

    return TransactionPlan(
        prep_detail=PreparationDetail(
            prep_input=final_input_list,
            prep_output=final_prep_list,
            reward_details=reward_details,
        ),
        group_details=final_group_list,
        network=network,
        script_method=method,
        allowed_ttl_slots=allow_ttl_slots,
        add_change_to_fee=add_change_to_fee,
    )


def add_bash_comment(comment):
    """
    Returns a bash comment that will be added in bash script
    :param comment:
    :return: bash comment list
    """
    return [
        "\n# ===================================================",
        comment,
        "# ===================================================",
    ]


def generate_bash_script(
    transaction_plan,
    signing_key_file_details,
    source_address,
    metadata_file=None,
    allow_ttl_slots=100,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    store_in_file=True,
    add_comments=False,
):
    """
    Generates the final bash script

    :param transaction_plan: Transaction Plan Object
    :param signing_key_file_details: File that will be used for signing the Transaction Files
    :param source_address: Source address
    :param allow_ttl_slots: Maximum Allowable TTL slots for the transactions (Default: 100)
    :param network: Network where the final bash script will connect and interact
    :param method: Method that will be used for connecting with Cardano
    :param store_in_file: Store the Script in a Bash File (Default: True)
    :param add_comments: Add comments in the Final Bash Script (Default: False)
    :return:
    """
    # Get settings
    masspayments_settings = get_script_settings()

    bash_script_list = ["#!/bin/bash"]

    # Include python version checking function
    if add_comments:
        bash_script_list += add_bash_comment(
            "# Find a possible python version for the script to use",
        )
    bash_script_list.append(FIND_PYTHON_FUNCTION)

    if not isinstance(transaction_plan, TransactionPlan):
        raise InvalidType(
            type=type(transaction_plan),
            message="Invalid Transaction Plan Type.",
        )
    if not isinstance(signing_key_file_details, dict):
        raise InvalidType(
            type=type(signing_key_file_details),
            message="Invalid Signing Key File Details Type.",
        )
    if not isinstance(source_address, str):
        raise InvalidType(
            type=type(source_address),
            message="Invalid Source Address Type.",
        )
    if not isinstance(allow_ttl_slots, int):
        raise InvalidType(
            type=type(allow_ttl_slots),
            message="Invalid Allowable TTL Slots Type.",
        )
    if not isinstance(store_in_file, bool):
        raise InvalidType(
            type=type(store_in_file),
            message="Invalid Store in File Type.",
        )
    if not isinstance(add_comments, bool):
        raise InvalidType(type=type(add_comments), message="Invalid Add Comments Type.")

    tx_uuid = transaction_plan.uuid

    prep_input_utxos = transaction_plan.prep_detail.prep_input
    prep_output_utxos = transaction_plan.prep_detail.prep_output
    group_details_list = transaction_plan.group_details
    prep_tx_submission_status = transaction_plan.prep_detail.submission_status
    reward_details = transaction_plan.prep_detail.reward_details

    # Set num_witness
    input_address_set = set()
    for input_utxo in prep_input_utxos:
        input_address_set.add(input_utxo.address)
    num_witness = len(input_address_set)

    pycardano_context = CACHE_VALUES.get("pycardano_context")

    prefix = masspayments_settings.command_prefix(method)
    if method == ScriptMethod.METHOD_PYCARDANO:
        prefix = pycardano_context.command_prefix
    network_flag = masspayments_settings.network_flag(network)

    # Additional Metadata File Command
    metadata_copy_command = None
    metadata_remove_command = None
    metadata_copy_filename = metadata_file
    if metadata_file and method in [
        ScriptMethod.METHOD_PYCARDANO,
        ScriptMethod.METHOD_DOCKER_CLI,
    ]:
        metadata_file_and_dir = os.path.split(metadata_file)
        metadata_copy_filename = (
            f"{check_and_create_temp_directory(ScriptMethod.METHOD_DOCKER_CLI)}"
            f"{metadata_file_and_dir[1]}"
        )
        metadata_copy_command = CREATE_FILE_COPY_TO_DOCKER.format(
            source_filename=metadata_file,
            filename=metadata_copy_filename,
            prefix=masspayments_settings.command_prefix(ScriptMethod.METHOD_DOCKER_CLI),
        )
        metadata_remove_command = DELETE_FILE.format(
            prefix=prefix,
            filename=metadata_copy_filename,
        )

    # Get TTL
    ttl = get_latest_slot_number(network=network, method=method) + allow_ttl_slots

    # Create Prep TX
    # Setup for Signing Key Files
    signing_key_file_setup_command_list = set()
    signing_key_file_delete_command_list = set()
    if method == ScriptMethod.METHOD_DOCKER_CLI or (
        method == ScriptMethod.METHOD_PYCARDANO and pycardano_context.use_docker_cli
    ):
        signing_key_files = set()
        for address in signing_key_file_details:
            new_signing_key_files = []
            for old_signing_key_file in signing_key_file_details[address]:
                signing_key_file_and_dir = os.path.split(old_signing_key_file)
                new_signing_key_file = f"{check_and_create_temp_directory(method)}{signing_key_file_and_dir[1]}"
                signing_key_files.add(new_signing_key_file)

                signing_key_file_setup_command_list.add(
                    CREATE_FILE_COPY_TO_DOCKER.format(
                        source_filename=old_signing_key_file,
                        filename=new_signing_key_file,
                        prefix=masspayments_settings.command_prefix(
                            ScriptMethod.METHOD_DOCKER_CLI,
                        ),
                    ),
                )
                signing_key_file_delete_command_list.add(
                    DELETE_FILE.format(
                        prefix=masspayments_settings.command_prefix(
                            ScriptMethod.METHOD_DOCKER_CLI,
                        ),
                        filename=new_signing_key_file,
                    ),
                )

                new_signing_key_files.append(new_signing_key_file)

            signing_key_file_details[address] = new_signing_key_files

    # Dust Collection Commands
    dust_commands = {}
    if transaction_plan.dust_group_details:
        for target_address in transaction_plan.dust_group_details:
            dust_order = 0
            dust_command_details = []
            for dust_prep_detail in transaction_plan.dust_group_details[target_address]:
                dust_txid_variable = (
                    f"txid_{tx_uuid}_dust_{target_address}_{dust_order}"
                )
                dust_prep_filename = f"{tx_uuid}_dust_{target_address}_{dust_order}"
                dust_prep_input = dust_prep_detail.prep_input
                dust_amount = sum([dust_input.amount for dust_input in dust_prep_input])
                dust_input_witnesses = set()
                for input_utxo in dust_prep_input:
                    dust_input_witnesses.add(input_utxo.address)
                    if input_utxo.dust_collected_utxo:
                        input_utxo.tx_hash = (
                            f"$txid_{tx_uuid}_dust_{target_address}_{dust_order-1}"
                        )
                dust_signing_file_parameters = []
                for address in dust_input_witnesses:
                    for dust_sk_file in signing_key_file_details[address]:
                        dust_signing_file_parameters.append(
                            f"--signing-key-file {dust_sk_file}",
                        )
                dust_command_details.append(
                    {
                        "create_command": create_transaction_command(
                            input_arg=dust_prep_input,
                            output_arg=dust_prep_detail.prep_output,
                            filename=f"{dust_prep_filename}.raw",
                            prefix=prefix,
                            metadata_filename=metadata_copy_filename,
                            fee=dust_amount - dust_prep_detail.prep_output[0].amount,
                            ttl=ttl,
                            is_draft=False,
                        ),
                        "sign_command": TRANSACTION_SIGN.format(
                            prefix=prefix,
                            raw_file=f"{dust_prep_filename}.raw",
                            signing_key_file_details=" ".join(
                                dust_signing_file_parameters,
                            ),
                            network=network_flag,
                            signed_file=f"{dust_prep_filename}.signed",
                        ),
                        "submit_command": TRANSACTION_SUBMIT.format(
                            prefix=prefix,
                            signed_file=f"{dust_prep_filename}.signed",
                            network=network_flag,
                        ),
                        "signed_tx_filename": f"{dust_prep_filename}.signed",
                        "submission_status": dust_prep_detail.submission_status,
                        "dust_txid_variable_name": dust_txid_variable,
                        "txid_command": f"{dust_txid_variable}=$("
                        + TRANSACTION_TXID.format(
                            prefix=prefix,
                            transaction_file=f"{dust_prep_filename}.signed",
                        )
                        + ")"
                        if dust_prep_detail.submission_status
                        in [
                            TransactionStatus.NOT_YET_SUBMITTED,
                            TransactionStatus.TTL_EXPIRED,
                        ]
                        else f'{dust_txid_variable}="{dust_prep_detail.tx_hash_id}"',
                    },
                )
                dust_order += 1
            dust_commands[target_address] = {
                "command_details": dust_command_details,
                "latest_dust_order": len(dust_command_details)
                - 1,  # Zero Based Indexes
            }

    # Fix Prep Input UTxOs that are based on dust collected utxos
    for input_utxo in prep_input_utxos:
        if input_utxo.dust_collected_utxo:
            dust_command_details = dust_commands[input_utxo.address]
            dust_tx_var = f"$txid_{tx_uuid}_dust_{input_utxo.address}_{dust_command_details['latest_dust_order']}"
            input_utxo.tx_hash = dust_tx_var

    if prep_tx_submission_status in [
        TransactionStatus.NOT_YET_SUBMITTED,
        TransactionStatus.TTL_EXPIRED,
    ]:
        prep_draft_filename = f"{tx_uuid}_prep.draft"
        prep_tx_draft_command = create_transaction_command(
            input_arg=prep_input_utxos,
            output_arg=prep_output_utxos,
            filename=prep_draft_filename,
            prefix=prefix,
            metadata_filename=metadata_copy_filename,
            reward_details=reward_details,
        )

        # Get Prep TX Fee
        protocol_filename = (
            "mainnet-protocol.json"
            if network == CardanoNetwork.MAINNET
            else "testnet-protocol.json"
        )
        prep_fee_command = TRANSACTION_FEE.format(
            prefix=prefix,
            draft_file=prep_draft_filename,
            num_input=len(prep_input_utxos),
            num_output=len(prep_output_utxos),
            network=network_flag,
            protocol_file=protocol_filename,
            num_witness=num_witness,
        )

        # Create Raw Prep TX File
        prep_raw_filename = f"{tx_uuid}_prep.raw"

        # Include Change
        prep_total_input_amount = sum(
            [utxo_detail.amount for utxo_detail in prep_input_utxos],
        )
        prep_total_input_amount += reward_details.get("stake_amount", 0)
        prep_total_output_amount = sum(
            [utxo_detail.amount for utxo_detail in prep_output_utxos],
        )
        prep_fee_str = "$prep_fee"
        if not transaction_plan.add_change_to_fee:
            prep_output_utxos.append(
                PaymentDetail(
                    address=source_address,
                    amount=f"$(({prep_total_input_amount - prep_total_output_amount}-prep_fee))",
                ),
            )
        else:
            prep_fee_str = f"{prep_total_input_amount - prep_total_output_amount}"

        prep_tx_raw_command = create_transaction_command(
            input_arg=prep_input_utxos,
            output_arg=prep_output_utxos,
            filename=prep_raw_filename,
            prefix=prefix,
            fee=prep_fee_str,
            ttl=ttl,
            metadata_filename=metadata_copy_filename,
            is_draft=False,
            reward_details=reward_details,
        )

        # Sign Prep TX
        raw_file = prep_raw_filename
        prep_tx_sign_commands = []
        prep_signed_filename = f"{tx_uuid}_prep.signed"
        signing_file_commands_list = []

        for address in input_address_set:
            for address_sk_file in signing_key_file_details[address]:
                signing_file_commands_list.append(
                    f"--signing-key-file {address_sk_file}",
                )

        prep_tx_sign_commands.append(
            TRANSACTION_SIGN.format(
                prefix=prefix,
                raw_file=raw_file,
                signing_key_file_details=" ".join(signing_file_commands_list),
                network=network_flag,
                signed_file=prep_signed_filename,
            ),
        )

        # Submit Signed Prep TX
        prep_tx_submit_command = TRANSACTION_SUBMIT.format(
            prefix=prefix,
            signed_file=prep_signed_filename,
            network=network_flag,
        )

        # Get TxID of prep transaction
        txid_command = TRANSACTION_TXID.format(
            prefix=prefix,
            transaction_file=prep_signed_filename,
        )
        txid_command = f"prep_txid=$({txid_command})"
    elif (
        transaction_plan.prep_detail.submission_status
        == TransactionStatus.SUBMISSION_ONGOING
    ):
        txid_command = f'prep_txid="{transaction_plan.prep_detail.tx_hash_id}"'
        prep_tx_submit_command = 'echo "Preparation Transaction Submitted"'
    else:
        txid_command = f'prep_txid="{transaction_plan.prep_detail.tx_hash_id}"'

    # Create Group Raw Files and Sign
    group_tx_raw_commands = []
    group_tx_sign_commands = []
    group_tx_submit_commands = []
    group_tx_allowed_index_list = []
    group_sk_file_param_list = []
    for group_sk_file in signing_key_file_details[source_address]:
        group_sk_file_param_list.append(f"--signing-key-file {group_sk_file}")
    group_signing_key_parameter = " ".join(group_sk_file_param_list)
    group_tx_ongoing_commands = []
    for group_detail in group_details_list:
        group_index = group_detail.index
        group_input_utxos = [
            InputUTXO(
                address=source_address,
                tx_hash="$(echo $prep_txid)",
                tx_index=group_index,
                amount=0,
            ),  # amount and address are not required here as the generated script only uses tx_hash and tx_index
        ]
        if group_detail.submission_status in [
            TransactionStatus.NOT_YET_SUBMITTED,
            TransactionStatus.TTL_EXPIRED,
            TransactionStatus.SUBMISSION_ONGOING,
        ]:
            if group_detail.submission_status in [
                TransactionStatus.NOT_YET_SUBMITTED,
                TransactionStatus.TTL_EXPIRED,
            ]:
                group_tx_raw_command = create_transaction_command(
                    input_arg=group_input_utxos,
                    output_arg=group_detail.payment_details,
                    filename=f"{tx_uuid}_{group_index}.raw",
                    prefix=prefix,
                    fee=group_detail.fee,
                    ttl=ttl,
                    metadata_filename=metadata_copy_filename,
                    is_draft=False,
                )
                group_tx_raw_commands.append(group_tx_raw_command)

                group_tx_sign_command = TRANSACTION_SIGN.format(
                    prefix=prefix,
                    raw_file=f"{tx_uuid}_{group_index}.raw",
                    signing_key_file_details=group_signing_key_parameter,
                    network=network_flag,
                    signed_file=f"{tx_uuid}_{group_index}.signed",
                )
                group_tx_sign_commands.append(group_tx_sign_command)

                group_tx_submit_command = TRANSACTION_SUBMIT.format(
                    prefix=prefix,
                    signed_file=f"{tx_uuid}_{group_index}.signed",
                    network=network_flag,
                )
                group_tx_submit_commands.append(
                    f"group_{group_index}_submit_result=$({group_tx_submit_command})",
                )

            group_tx_allowed_index_list.append(f"{group_index}")
            group_txid_command = TRANSACTION_TXID.format(
                prefix=prefix,
                transaction_file=f"{tx_uuid}_{group_index}.signed",
            )
            group_tx_ongoing_commands += [
                f"group_{group_index}_txid=$({group_txid_command})",
                GROUP_TX_ONGOING_FUNCTION_CALL.format(
                    group_tx_index=group_index,
                    txid=f"$group_{group_index}_txid",
                ),
            ]

    # Create Final Bash Script

    if metadata_copy_command:
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Create a copy of the Metadata JSON File in docker container",
            )
        bash_script_list.append(metadata_copy_command)

    if signing_key_file_setup_command_list:
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Create a copy of the signing key files in docker container",
            )
        bash_script_list += list(signing_key_file_setup_command_list)

    if prep_tx_submission_status in [
        TransactionStatus.NOT_YET_SUBMITTED,
        TransactionStatus.TTL_EXPIRED,
    ]:
        if dust_commands:
            if add_comments:
                bash_script_list += add_bash_comment("# Create Dust UTxOs")
            bash_script_list.append(
                'echo -en "Creating and Signing Dust Transaction Raw Files"',
            )
            for target_address in dust_commands:
                dust_command_details = dust_commands[target_address]
                for dust_command_detail in dust_command_details["command_details"]:
                    bash_script_list.append(dust_command_detail["create_command"])
                    bash_script_list.append(dust_command_detail["sign_command"])
                    bash_script_list.append(dust_command_detail["txid_command"])
            bash_script_list += [
                'echo -en "\\r\\033[KDust Transaction Raw Files Created and Signed"',
                "echo",
            ]

        if add_comments:
            bash_script_list += add_bash_comment(
                "# Create the Preparation Transaction Draft File",
            )
        bash_script_list.append(prep_tx_draft_command)
        if add_comments:
            bash_script_list += add_bash_comment("# Find Preparation Transaction Fee")
        bash_script_list.append(f"prep_fee=$({prep_fee_command})")
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Since prep_fee result follows the format <fee> Lovelace, "
                "we need to remove the 'Lovelace' part of the response",
            )
        bash_script_list.append("prep_fee=$(echo ${prep_fee// Lovelace/})")

        if transaction_plan.add_change_to_fee:
            bash_script_list += add_bash_comment("# Add change to fee")
            change_amount = prep_total_input_amount - prep_total_output_amount
            bash_script_list.append(
                f'echo "Preparation Transaction Change, amounting to $(({change_amount} - prep_fee)) Lovelace, '
                f'will be added to the preparation fee making the total fee {change_amount} Lovelace"',
            )

        if add_comments:
            bash_script_list += add_bash_comment(
                "# Create the Preparation Transaction Raw File",
            )
        bash_script_list.append('echo -en "Creating Preparation Transaction Raw File"')
        bash_script_list.append(prep_tx_raw_command)
        bash_script_list += [
            'echo -en "\\r\\033[KPreparation Transaction Raw File Created"',
            "echo",
        ]
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Sign the Preparation Transaction Raw File",
            )
        bash_script_list.append('echo -en "Signing Preparation Transaction Raw File"')
        bash_script_list += prep_tx_sign_commands
        bash_script_list += [
            'echo -en "\\r\\033[KPreparation Transaction Raw File Signed"',
            "echo",
        ]

    if add_comments:
        bash_script_list += add_bash_comment("# Get the Preparation Transaction ID")
    bash_script_list.append(txid_command)

    if group_tx_raw_commands:
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Create the Group Transaction Raw Files",
            )
        bash_script_list.append('echo -en "Creating Group Transaction Raw Files"')
        bash_script_list += group_tx_raw_commands
        bash_script_list += [
            'echo -en "\\r\\033[KGroup Transaction Raw Files Created"',
            "echo",
        ]

    if group_tx_sign_commands:
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Sign the Group Transaction Raw Files",
            )
        bash_script_list.append('echo -en "Signing Group Transaction Raw Files"')
        bash_script_list += group_tx_sign_commands
        bash_script_list += [
            'echo -en "\\r\\033[KGroup Transaction Raw Files Signed"',
            "echo",
        ]

    if add_comments:
        bash_script_list += add_bash_comment("# Transaction Status Setup")
    bash_script_list.append(STATUS_MESSAGE_SETUP)

    if add_comments:
        bash_script_list += add_bash_comment("# Getting Latest Slot Number Function")
    bash_script_list.append(
        LATEST_SLOT_NUMBER_BASH_FUNCTION.format(
            tip_query=QUERY_TIP.format(prefix=prefix, network=network_flag),
            python_exec_str="$python_exec_str",
        ),
    )

    if dust_commands:
        dust_not_yet_submitted = 0
        for target_address in dust_commands:
            dust_command_list = dust_commands[target_address]
            map_index = 0
            for dust_command_detail in dust_command_list["command_details"]:
                if dust_command_detail["submission_status"] in [
                    TransactionStatus.NOT_YET_SUBMITTED,
                    TransactionStatus.TTL_EXPIRED,
                ]:
                    dust_not_yet_submitted += 1

        if dust_not_yet_submitted > 0:
            if add_comments:
                bash_script_list += add_bash_comment(
                    "# Function for handling Dust Transaction Submission",
                )

            bash_script_list.append(
                DUST_TX_SUBMIT_SCRIPT.format(
                    polling_arg_index=5,
                    dust_submit_command=TRANSACTION_SUBMIT.format(
                        prefix=prefix,
                        signed_file="$1",
                        network=network_flag,
                    ),
                    utxo_query_command=QUERY_WALLET_UTXO_NO_FILE.format(
                        prefix=prefix,
                        address="$2",
                        network=network_flag,
                    ),
                    function_index_txid=3,
                    ongoing_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                        transaction_plan_filename=transaction_plan.filename,
                        python_update_command=f"data['dust_group_details']['$2'][$4]['submission_status']="
                        f"'{TransactionStatus.SUBMISSION_ONGOING.value}';"
                        f"data['dust_group_details']['$2'][$4]['tx_hash_id']='$3'",
                        python_exec_str="$python_exec_str",
                    ),
                    expired_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                        transaction_plan_filename=transaction_plan.filename,
                        python_update_command=f"data['dust_group_details']['$2'][$4]['submission_status']="
                        f"'{TransactionStatus.TTL_EXPIRED.value}'",
                        python_exec_str="$python_exec_str",
                    ),
                    success_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                        transaction_plan_filename=transaction_plan.filename,
                        python_update_command=f"data['dust_group_details']['$2'][$4]['submission_status']="
                        f"'{TransactionStatus.SUBMISSION_DONE.value}';"
                        f"data['dust_group_details']['$2'][$4]['tx_hash_id']='$3'",
                        python_exec_str="$python_exec_str",
                    ),
                    ttl=ttl,
                ),
            )
        for target_address in dust_commands:
            dust_command_list = dust_commands[target_address]
            map_index = 0
            for dust_command_detail in dust_command_list["command_details"]:
                if dust_command_detail["submission_status"] in [
                    TransactionStatus.NOT_YET_SUBMITTED,
                    TransactionStatus.TTL_EXPIRED,
                    TransactionStatus.SUBMISSION_ONGOING,
                ]:
                    bash_script_list.append(
                        DUST_SUBMIT_FUNCTION_CALL.format(
                            signed_file_name=dust_command_detail["signed_tx_filename"],
                            target_address=target_address,
                            txid_variable_name=f"${dust_command_detail['dust_txid_variable_name']}",
                            map_index=map_index,
                            straight_to_poll=str(
                                dust_command_detail["submission_status"]
                                == TransactionStatus.SUBMISSION_ONGOING,
                            ).lower(),
                        ),
                    )
                map_index += 1
            if dust_not_yet_submitted > 0:
                bash_script_list.append('echo "Dust Transactions Submission Done"')

    if prep_tx_submission_status in [
        TransactionStatus.NOT_YET_SUBMITTED,
        TransactionStatus.TTL_EXPIRED,
        TransactionStatus.SUBMISSION_ONGOING,
    ]:
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Submit the Preparation Transaction Signed Files",
            )
        wallet_query = QUERY_WALLET_UTXO_NO_FILE.format(
            prefix=prefix,
            address=source_address,
            network=network_flag,
        )
        bash_script_list.append(
            POST_PREP_TX_SUBMIT_SCRIPT.format(
                prep_submit_command=prep_tx_submit_command,
                utxo_query_command=wallet_query,
                prep_txid_variable="prep_txid",
                ttl=ttl,
                ongoing_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                    transaction_plan_filename=transaction_plan.filename,
                    python_update_command=f"data['prep_detail']['submission_status']="
                    f"'{TransactionStatus.SUBMISSION_ONGOING.value}';"
                    f"data['prep_detail']['tx_hash_id']='$prep_txid'",
                    python_exec_str="$python_exec_str",
                ),
                expired_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                    transaction_plan_filename=transaction_plan.filename,
                    python_update_command=f"data['prep_detail']['submission_status']="
                    f"'{TransactionStatus.TTL_EXPIRED.value}'",
                    python_exec_str="$python_exec_str",
                ),
                success_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                    transaction_plan_filename=transaction_plan.filename,
                    python_update_command=f"data['prep_detail']['submission_status']="
                    f"'{TransactionStatus.SUBMISSION_DONE.value}';"
                    f"data['prep_detail']['tx_hash_id']='$prep_txid'",
                    python_exec_str="$python_exec_str",
                ),
            ),
        )

    group_tx_submit_and_ongoing_commands = (
        group_tx_submit_commands + group_tx_ongoing_commands
    )
    if len(group_tx_submit_and_ongoing_commands):
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Submit the Group Transaction Signed Files",
            )
        if group_tx_submit_commands:
            bash_script_list.append(
                'echo "Submitting Signed Group Transactions to Cardano"',
            )

        # Set Group TX to ongoing function
        bash_script_list.append(
            GROUP_TX_ONGOING_SET_FUNCTION_SCRIPT.format(
                ongoing_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                    transaction_plan_filename=transaction_plan.filename,
                    python_update_command=f"data['group_details'][$1]['submission_status']="
                    f"'{TransactionStatus.SUBMISSION_ONGOING.value}';"
                    f"data['group_details'][$1]['tx_hash_id']='$2'",
                    python_exec_str="$python_exec_str",
                ),
            ),
        )

        bash_script_list += group_tx_submit_commands

        if add_comments:
            bash_script_list += add_bash_comment("# Wait for the Group Transactions")
        bash_script_list.append(
            TX_STATUS_SCRIPT.format(
                transaction_txid_query=TRANSACTION_TXID.format(
                    prefix=prefix,
                    transaction_file=f"{tx_uuid}_$group_index.signed",
                ),
                utxo_status_bash_array_str=" ".join(
                    "$ongoing_str" for _ in range(len(group_tx_allowed_index_list))
                ),
                utxo_index_array_str=" ".join(group_tx_allowed_index_list),
                prep_txid_variable="prep_txid",
                utxo_query_command=QUERY_WALLET_UTXO_VIA_TXID.format(
                    prefix=prefix,
                    tx_hash="$prep_txid",
                    tx_index="$group_index",
                    network=network_flag,
                ),
                ttl=ttl,
                expired_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                    transaction_plan_filename=transaction_plan.filename,
                    python_update_command=f"data['group_details'][$group_index]['submission_status']="
                    f"'{TransactionStatus.TTL_EXPIRED.value}'",
                    python_exec_str="$python_exec_str",
                ),
                success_status_command=UPDATE_TRANSACTION_PLAN_FILE.format(
                    transaction_plan_filename=transaction_plan.filename,
                    python_update_command=f"data['group_details'][$group_index]['submission_status']="
                    f"'{TransactionStatus.SUBMISSION_DONE.value}';"
                    f"data['group_details'][$group_index]['tx_hash_id']='$group_txid'",
                    python_exec_str="$python_exec_str",
                ),
            ),
        )

    if method == ScriptMethod.METHOD_DOCKER_CLI or (
        method == ScriptMethod.METHOD_PYCARDANO and pycardano_context.use_docker_cli
    ):
        if add_comments:
            bash_script_list += add_bash_comment(
                "# Remove the file copies in docker container",
            )
        bash_script_list += list(signing_key_file_delete_command_list)
        if metadata_remove_command:
            bash_script_list.append(metadata_remove_command)

    bash_script = "\n".join(bash_script_list)

    if store_in_file:
        script_filename = f"{tx_uuid}.sh"
        with open(script_filename, "w+") as script_file:
            script_file.write(bash_script)
        return script_filename

    return bash_script
