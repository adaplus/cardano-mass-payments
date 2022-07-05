import argparse
import copy
import json
import os
import traceback
import uuid

from ..cache import CACHE_VALUES
from ..classes import SourceAddressDetail, TransactionPlan
from ..constants.common import (
    CardanoNetwork,
    DustCollectionMethod,
    ScriptMethod,
    ScriptOutputFormats,
)
from ..constants.exceptions import (
    InvalidFileError,
    InvalidMethod,
    InvalidNetwork,
    ScriptError,
)
from ..utils.cli_utils import create_file_copy_in_docker_container, delete_temp_file
from ..utils.common import print_to_console, subprocess_popen
from ..utils.pycardano_utils import CardanoCLIChainContext
from ..utils.script_utils import (
    adjust_utxos,
    dust_collect,
    generate_bash_script,
    parse_sources_csv_file,
    preparation_step,
)


def adjust_metadata_message(metadata_message, max_bytes=64):
    """
    Function that adjust the metadata message based on the maximum bytes

    :param metadata_message: Metadata Message String
    :param max_bytes: Maximum Bytes Required for each Metadata Message
    :return: List of Metadata Messages that follows the maximum byte size
    """
    adjusted_metadata_message = []

    metadata_message_list = copy.deepcopy(metadata_message)

    line_index = 0
    for message_line in metadata_message_list:
        if len(message_line.encode("utf-8")) <= max_bytes:
            adjusted_metadata_message.append(message_line)
        else:
            # Per Word
            adjusted_line_list = []
            extras_list = []
            message_words = message_line.split(" ")
            limit_reached = False
            for message_word in message_words:
                adjusted_line = " ".join(adjusted_line_list + [message_word])
                if len(adjusted_line.encode("utf-8")) <= max_bytes:
                    adjusted_line_list.append(message_word)
                elif not limit_reached:
                    # Per Character
                    final_char_index = -1
                    for char_index in range(len(message_word)):
                        adjusted_line = " ".join(
                            adjusted_line_list + [message_word[: char_index + 1]],
                        )
                        if len(adjusted_line.encode("utf-8")) <= max_bytes:
                            final_char_index = char_index
                        else:
                            # It is now at limit
                            limit_reached = True
                            break
                    # Add the adjusted word in adjusted line list
                    if final_char_index >= 0:
                        temp_char_index = final_char_index + 1
                        adjusted_line_list.append(message_word[:temp_char_index])
                        extras_list.append(message_word[temp_char_index:])
                else:
                    extras_list.append(message_word)
            adjusted_metadata_message.append(" ".join(adjusted_line_list))
            if extras_list:
                metadata_message_list.insert(line_index + 1, " ".join(extras_list))
        line_index += 1

    return adjusted_metadata_message


def get_source_details(args, transaction_plan):
    """
    Gets the source address and signing key file from command arguments/transaction plan

    :param args: Command Arguments
    :param transaction_plan: TransactionPlan object
    :return: Tuple containing source address, signing key file, and source details
    """
    source_address = args.source_address
    signing_key_file = args.source_signing_key_file
    output_format = ScriptOutputFormats(args.output_type)

    if transaction_plan and transaction_plan.source_details:
        source_details = {}
        for source_detail in transaction_plan.source_details:
            source_details[source_detail.address] = source_detail.signing_key_file
            if source_detail.is_main_source_address:
                source_address = source_detail.address
                signing_key_file = source_detail.signing_key_file
    else:
        source_details = parse_sources_csv_file(args.sources_csv)

    # Set source address
    if source_address is None:
        source_address = next(
            iter(source_details),
        )  # Use the first address as the source address
        print_to_console(
            f"Source Address not provided. Will use {source_address}",
            output_format,
        )

    if signing_key_file:
        if isinstance(signing_key_file, list):
            source_details[source_address] = signing_key_file
        else:
            source_details[source_address] = [signing_key_file]
    elif source_details.get(source_address):
        signing_key_file = source_details.get(source_address)
        print_to_console(
            f"Signing Key File not provided. Will use {signing_key_file}",
            output_format,
        )
    else:
        raise ScriptError(
            message="No signing key file found in Source CSV, please include signing key for address.",
            additional_context={"address": source_address},
        )

    return source_address, signing_key_file, source_details


def get_metadata_details(args, transaction_plan, metadata_json_filename):
    """
    Get and set metadata details on cache

    :param args: Command Arguments
    :param transaction_plan: TransactionPlan object
    :param metadata_json_filename: Metadata JSON template filename
    :return: updated metadata json filename
    """
    output_format = ScriptOutputFormats(args.output_type)
    script_method = (
        transaction_plan.script_method
        if transaction_plan
        else ScriptMethod(args.script_method)
    )

    # Check Metadata JSON File
    metadata_json_details = None
    if metadata_json_filename:
        # Check if json file is json loadable
        with open(metadata_json_filename, "r") as metadata_json_file:
            try:
                metadata_json_details = json.loads(metadata_json_file.read())
            except Exception:
                print_to_console(
                    "Invalid metadata json file. Please make sure that the file is correct.",
                    output_format,
                )
                return

    metadata_message_filename = args.metadata_message_file
    if metadata_message_filename:
        with open(metadata_message_filename, "r") as metadata_message_file:
            metadata_message = metadata_message_file.read().split("\n")
        metadata_json_details = metadata_json_details or {}
        metadata_json_details.update(
            {"674": {"msg": adjust_metadata_message(metadata_message)}},
        )
        # Create a new metadata file
        if metadata_json_filename is None:
            metadata_message_file_str_split = os.path.split(metadata_message_filename)
            metadata_message_dir = metadata_message_file_str_split[0]
            metadata_json_filename = f"{uuid.uuid4().hex}_metadata.json"
            if metadata_message_dir != "":
                metadata_json_filename = (
                    f"{metadata_message_dir}/{metadata_json_filename}"
                )
        metadata_json_file_str_split = os.path.split(metadata_json_filename)
        metadata_json_dir = metadata_json_file_str_split[0]
        metadata_json_filename = f"new_{metadata_json_file_str_split[1]}"
        if metadata_json_dir != "":
            metadata_json_filename = f"{metadata_json_dir}/{metadata_json_filename}"
        if transaction_plan and transaction_plan.metadata:
            metadata_json_filename = f"{transaction_plan.uuid}_metadata.json"
        print_to_console(
            f"Generated a new metadata file to incorporate the metadata message '{metadata_json_filename}'",
            output_format=output_format,
        )
        with open(metadata_json_filename, "w+") as metadata_json_file:
            metadata_json_file.write(json.dumps(metadata_json_details))

    if metadata_json_filename:
        # Create a temp copy in docker container if method == DOCKER_CLI
        metadata_copy_filename = metadata_json_filename
        if script_method == ScriptMethod.METHOD_DOCKER_CLI:
            metadata_copy_filename = create_file_copy_in_docker_container(
                metadata_json_filename,
            )
        CACHE_VALUES[
            "metadata_file"
        ] = metadata_copy_filename  # Update the source signing key file cache value

    return metadata_json_filename


def get_command_parameters(args):
    """
    Gets the Command Parameters

    :param args: Command Arguments
    :return: Map containing the Command Parameters
    """

    # Create Preparation TX Details
    output_format = ScriptOutputFormats(args.output_type)
    CACHE_VALUES["output_format"] = output_format
    metadata_json_filename = args.metadata_json_file

    # Update Settings
    if args.magic_number:
        CACHE_VALUES["settings"].cardano_testnet_magic = args.magic_number

    transaction_plan = None
    if args.transaction_plan_file:
        print_to_console("Transaction Plan Found, Parsing...", output_format)
        try:
            transaction_plan = TransactionPlan.from_transaction_plan_file(
                args.transaction_plan_file,
            )
        except InvalidNetwork as e:
            raise e
        except InvalidMethod as e:
            raise e
        except Exception as e:
            raise InvalidFileError(
                file=args.transaction_plan_file,
                message="Error during Parsing Transaction Plan File.",
                error=e,
                traceback=traceback.format_exc(),
            )

        if transaction_plan.metadata:
            metadata_json_filename = f"{transaction_plan.uuid}_metadata.json"
            with open(metadata_json_filename, "w+") as metadata_json_file:
                metadata_json_file.write(json.dumps(transaction_plan.metadata))

    try:
        cardano_network = (
            transaction_plan.network
            if transaction_plan
            else CardanoNetwork(args.cardano_network)
        )
    except ValueError:
        raise InvalidNetwork(network=args.cardano_network)

    try:
        script_method = (
            transaction_plan.script_method
            if transaction_plan
            else ScriptMethod(args.script_method)
        )
    except ValueError:
        raise InvalidMethod(method=args.script_method)

    if script_method == ScriptMethod.METHOD_PYCARDANO:
        if args.include_rewards:
            # Rewards withdrawal is not supported for Pycardano Method
            raise ScriptError(
                message="Rewards withdrawal is not supported for Pycardano Method",
            )

        # Create pycardano context object
        CACHE_VALUES["pycardano_context"] = CardanoCLIChainContext(
            cardano_network=cardano_network,
            use_docker_cli=args.use_docker_cli_for_pycardano,
        )

    store_in_file = output_format in [
        ScriptOutputFormats.BASH_SCRIPT,
        ScriptOutputFormats.JSON,
    ]
    allowed_ttl_slots = (
        transaction_plan.allowed_ttl_slots
        if transaction_plan
        else args.allowed_ttl_slots
    )

    try:
        source_address, signing_key_file, source_details = get_source_details(
            args,
            transaction_plan,
        )
    except FileNotFoundError as e:
        raise InvalidFileError(
            file=e.filename,
            message="Source File does not exist.",
        )

    CACHE_VALUES[
        "source_address"
    ] = source_address  # Update the source address cache value
    CACHE_VALUES[
        "source_signing_key_file"
    ] = signing_key_file  # Update the source signing key file cache value

    try:
        metadata_json_filename = get_metadata_details(
            args,
            transaction_plan,
            metadata_json_filename,
        )
    except Exception as e:
        error_filename = metadata_json_filename or args.metadata_message_file
        if isinstance(e, FileNotFoundError):
            error_filename = e.filename
        raise InvalidFileError(
            file=error_filename,
            message="Error while getting metadata details",
            error=e,
            traceback=traceback.format_exc(),
        )

    # Dust collection details
    dust_collection_method = DustCollectionMethod(args.dust_collection_method)
    dust_collection_threshold = args.dust_collection_threshold
    if transaction_plan:
        dust_collection_method = transaction_plan.dust_collection_method
        dust_collection_threshold = transaction_plan.dust_collection_threshold

    return {
        "output_format": output_format,
        "source_address": source_address,
        "source_details": source_details,
        "cardano_network": cardano_network,
        "script_method": script_method,
        "allowed_ttl_slots": allowed_ttl_slots,
        "metadata_json_filename": metadata_json_filename,
        "store_in_file": store_in_file,
        "add_comments": args.add_comments,
        "payments_csv_file": args.payments_csv,
        "transaction_plan_file": transaction_plan,
        "dust_collection_method": dust_collection_method,
        "dust_collection_threshold": dust_collection_threshold,
        "enable_dust_collection": args.enable_dust_collection,
        "enable_immediate_execution": args.execute_script_now,
        "include_rewards": args.include_rewards,
    }


def generate_transaction_plan(
    output_format,
    source_address,
    source_details,
    payments_csv_file,
    cardano_network,
    script_method,
    allowed_ttl_slots,
    enable_dust_collection=False,
    dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE,
    dust_collection_threshold=10000000,
    include_rewards=False,
):
    """
    Generate Transaction Plan

    :param output_format: Script Output Format
    :param source_address: Source Address
    :param source_details: Map containing Address + Signing Key File Details
    :param payments_csv_file: CSV File containing Payment Details
    :param cardano_network: Network where the script connects to
    :param script_method: Method used in the script logic
    :param allowed_ttl_slots: Number of slots allowed before the transaction to be deemed invalid
    :param enable_dust_collection: Flag on whether to execute dust collection or not
    :param dust_collection_method: Method that will be used for dust collection
    :param dust_collection_threshold: Maximum amount that will be the basis for dust collection
    :param include_rewards: Flag on whether to include getting the stake rewards
    :return: TransactionPlan object
    """
    print_to_console("Creating Preparation TX and Initial Groupings...", output_format)
    init_details = preparation_step(
        source_address,
        source_details,
        payments_csv_file,
        network=cardano_network,
        method=script_method,
        include_rewards=include_rewards,
    )

    if init_details.get("require_dust_collection"):
        if enable_dust_collection:
            init_details = dust_collect(
                input_utxos=init_details.get("wallet_utxos"),
                payment_group_details=init_details.get("output_details"),
                transaction_draft_filename=init_details.get("transaction_filename"),
                max_tx_size=init_details.get("max_tx_size"),
                source_address=source_address,
                source_details=source_details,
                network=cardano_network,
                method=script_method,
                dust_collection_method=dust_collection_method,
                dust_collection_threshold=dust_collection_threshold,
                reward_details=init_details.get("stake_reward_details", {}),
            )
        else:
            raise ScriptError(
                "Dust collection process is required but dust collection is disabled. "
                "You can enable it by adding --enable-dust-collection",
            )

    # Adjust UTxO Groups
    print_to_console("Adjusting Payment UTxO Groups...", output_format)
    transaction_plan = adjust_utxos(
        init_details.get("output_details"),
        init_details.get("wallet_utxos"),
        init_details.get("transaction_filename"),
        source_address,
        init_details.get("max_tx_size"),
        reward_details=init_details.get("stake_reward_details", {}),
        allow_ttl_slots=allowed_ttl_slots,
        network=cardano_network,
        method=script_method,
    )

    # Incorporate Source Details in Transaction Plan
    transaction_plan.dust_group_details = init_details.get("dust_group_details", {})
    transaction_plan.source_details = [
        SourceAddressDetail(
            address=source_detail_key,
            signing_key_file=source_details[source_detail_key],
            is_main_source_address=(source_detail_key == source_address),
        )
        for source_detail_key in source_details
    ]

    return transaction_plan


def generate_script_process(args):
    """
    Main process of generating the masspayments script

    :param args: Command Argument Parameters
    :return: TransactionPlan object record
    """
    command_parameters = get_command_parameters(args)

    output_format = command_parameters.get("output_format")
    source_details = command_parameters.get("source_details")
    source_address = command_parameters.get("source_address")
    metadata_json_filename = command_parameters.get("metadata_json_filename")
    allowed_ttl_slots = command_parameters.get("allowed_ttl_slots")
    store_in_file = command_parameters.get("store_in_file")
    cardano_network = command_parameters.get("cardano_network")
    script_method = command_parameters.get("script_method")

    transaction_plan = (
        generate_transaction_plan(
            output_format=output_format,
            source_address=source_address,
            source_details=source_details,
            payments_csv_file=command_parameters.get("payments_csv_file"),
            cardano_network=cardano_network,
            script_method=script_method,
            allowed_ttl_slots=allowed_ttl_slots,
            dust_collection_method=command_parameters.get("dust_collection_method"),
            dust_collection_threshold=command_parameters.get(
                "dust_collection_threshold",
            ),
            enable_dust_collection=command_parameters.get("enable_dust_collection"),
            include_rewards=command_parameters.get("include_rewards"),
        )
        if command_parameters.get("transaction_plan_file") is None
        else command_parameters.get("transaction_plan_file")
    )
    if metadata_json_filename:
        with open(metadata_json_filename, "r") as metadata_json_file:
            transaction_plan.metadata = json.loads(metadata_json_file.read())

    # Create Transaction Plan File
    transaction_plan_filename = (
        transaction_plan.filename or f"{transaction_plan.uuid}_transaction_plan.json"
    )
    with open(transaction_plan_filename, "w+") as transaction_plan_file:
        transaction_plan_file.write(transaction_plan.json())

    if output_format == ScriptOutputFormats.TRANSACTION_PLAN:
        print_to_console(
            json.dumps({"transaction_plan_file": transaction_plan_filename}),
            output_format,
        )
        return transaction_plan

    # Generating Bash Script
    print_to_console("Generating the final Bash Script...", output_format)
    bash_script_result = generate_bash_script(
        transaction_plan,
        source_details,
        source_address,
        metadata_file=metadata_json_filename,
        allow_ttl_slots=allowed_ttl_slots,
        add_comments=args.add_comments,
        store_in_file=store_in_file,
        network=cardano_network,
        method=script_method,
    )

    if script_method == ScriptMethod.METHOD_DOCKER_CLI and CACHE_VALUES.get(
        "metadata_file",
    ):
        delete_temp_file(
            filename=CACHE_VALUES.get("metadata_file"),
            method=script_method,
        )

    if output_format == ScriptOutputFormats.BASH_SCRIPT:
        print_to_console(
            f"Script Generated, stored in {bash_script_result}",
            output_format,
        )
    elif output_format == ScriptOutputFormats.JSON:
        print_to_console(
            json.dumps(
                {
                    "script_file": bash_script_result,
                },
            ),
            output_format,
        )
    elif output_format == ScriptOutputFormats.CONSOLE:
        print_to_console("Generated Script:", output_format)
        print_to_console("-------------------------------------", output_format)
        print_to_console(bash_script_result, output_format)

    if command_parameters.get("enable_immediate_execution"):
        # Regardless of Output Format, this will be printed in console
        print("Transaction Plan Details:")
        print("-------------------------------------")
        print(transaction_plan.general_transaction_details())
        chosen_execute_option = (
            input(
                "You specified immediate execution of the transaction plan. "
                "You may review the transaction plan above. "
                "Are you sure you wish to continue and execute this plan? [YES/No] : ",
            ).lower()
            or "yes"
        )
        while chosen_execute_option not in ["yes", "no"]:
            chosen_execute_option = (
                input("Please select from the following options [YES/No] : ").lower()
                or "yes"
            )
        if chosen_execute_option == "no":
            print("Thank you for using the MassPayments Script")
            return transaction_plan
        print("-------------------------------------")
        subprocess_popen(["bash", f"{transaction_plan.uuid}.sh"], print_output=True)

    return transaction_plan


def main():
    parser = argparse.ArgumentParser()

    # --cardano-network TESTNET --script-method DOCKER_CLI --output-type BASH_SCRIPT --sources-csv sources.csv
    # --payments-csv payments.csv --source-address address --source-signing-key-file sign_key_file.json
    # --metadata-json-file metadata.json --allowed-ttl-slots 1000 --dust-collection-method COLLECT_TO_SOURCE
    # --dust-collection-threshold 10000000 --add-comments
    parser.add_argument(
        "--cardano-network",
        help="Network which the script will connect to",
        default=CardanoNetwork.TESTNET.value,
        choices=[cn.value for cn in CardanoNetwork],
    )
    parser.add_argument(
        "--script-method",
        help="Method that will be used in generating the script",
        default=ScriptMethod.METHOD_DOCKER_CLI.value,
        choices=[cf.value for cf in ScriptMethod],
    )
    parser.add_argument(
        "--output-type",
        help="Format of the output script",
        default=ScriptOutputFormats.JSON.value,
        choices=[sof.value for sof in ScriptOutputFormats],
    )
    parser.add_argument(
        "--sources-csv",
        help="CSV file that contains the source+signing key file details",
        required=True,
    )
    parser.add_argument(
        "--payments-csv",
        help="CSV file that contains the output utxo details",
        required=True,
    )
    parser.add_argument(
        "--add-comments",
        help="Option to add comments in the generated script",
        nargs="?",
        default=False,
        const=True,
    )
    parser.add_argument(
        "--use-docker-cli-for-pycardano",
        help="Option use docker cli if method used is PyCardano",
        nargs="?",
        default=False,
        const=True,
    )
    parser.add_argument(
        "--enable-dust-collection",
        help="Option to enable dust collection process",
        nargs="?",
        default=False,
        const=True,
    )
    parser.add_argument(
        "--execute-script-now",
        help="Immediately Execute the Generated Script",
        nargs="?",
        default=False,
        const=True,
    )
    parser.add_argument(
        "--include-rewards",
        help="Include Main Source Address Stake Rewards",
        nargs="?",
        default=False,
        const=True,
    )
    parser.add_argument(
        "--allowed-ttl-slots",
        help="Number of allowable slots for the Transaction TTL",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--magic-number",
        help="Cardano Network Magic Number",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--dust-collection-method",
        help="Method to be used for dust collection",
        default=DustCollectionMethod.COLLECT_TO_SOURCE.value,
        choices=[dcm.value for dcm in DustCollectionMethod],
    )
    parser.add_argument(
        "--dust-collection-threshold",
        help="Amount that will serve as the criteria for dust collection",
        type=int,
        default=10000000,
    )
    parser.add_argument("--source-address", help="Source Address")
    parser.add_argument("--source-signing-key-file", help="Source Signing Key File")
    parser.add_argument("--metadata-json-file", help="Metadata JSON File")
    parser.add_argument("--metadata-message-file", help="Metadata Message File")
    parser.add_argument("--transaction-plan-file", help="Transaction Plan File")

    # Check arguments
    args = parser.parse_args()

    try:
        generate_script_process(args)
    except ScriptError as e:
        print_to_console(e, output_format=ScriptOutputFormats(args.output_type))
    except Exception as e:
        print_to_console(
            ScriptError(
                message="Unexpected Error in Script Process Generation.",
                error=e,
                traceback=traceback.format_exc(),
            ),
            output_format=ScriptOutputFormats(args.output_type),
        )


if __name__ == "__main__":
    main()
