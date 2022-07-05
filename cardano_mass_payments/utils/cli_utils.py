import json
import os
import subprocess
import tempfile
import traceback
import uuid

from pycardano import Address
from pycardano import Network as PycardanoNetwork
from pycardano import (
    PaymentSigningKey,
    Transaction,
    TransactionBody,
    TransactionBuilder,
    TransactionInput,
    TransactionOutput,
    UTxO,
    VerificationKeyWitness,
)
from pycardano.metadata import AlonzoMetadata, AuxiliaryData
from pycardano.plutus import ExecutionUnits
from pycardano.utils import fee as get_pycardano_fee

from ..cache import CACHE_VALUES
from ..classes import InputUTXO
from ..constants.commands import (
    CHECK_TEMP_DIRECTORY,
    CREATE_FILE_COPY_TO_DOCKER,
    DELETE_FILE,
    INSPECT_ADDRESS_COMMAND,
    INSPECT_ADDRESS_DOCKER_COMMAND,
    QUERY_PROTOCOL_PARAMETERS,
    QUERY_PROTOCOL_PARAMETERS_WITH_FILE,
    QUERY_TIP,
    QUERY_WALLET_UTXO,
    READ_FILE,
    STAKE_ADDRESS_CONVERT_COMMAND,
    STAKE_ADDRESS_FROM_STAKE_HASH_COMMAND,
    STAKE_REWARDS_COMMAND,
    TRANSACTION_BUILD,
    TRANSACTION_FEE,
    TRANSACTION_SIGN,
    TRANSACTION_TXID,
)
from ..constants.common import CardanoNetwork, ScriptMethod
from ..constants.exceptions import (
    EmptyList,
    InvalidFileError,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from .common import get_script_settings, print_to_console, subprocess_popen


def check_and_create_temp_directory(method=ScriptMethod.METHOD_DOCKER_CLI):
    """
    Get/Create the temporary directory that will be used in the script
    :param method: Method used to get the temporary directory
    :return: temporary directory string
    """
    temp_directory = ""
    masspayments_settings = get_script_settings()
    pycardano_context = CACHE_VALUES.get("pycardano_context")
    if method == ScriptMethod.METHOD_DOCKER_CLI or (
        method == ScriptMethod.METHOD_PYCARDANO and pycardano_context.use_docker_cli
    ):
        prefix = masspayments_settings.command_prefix(ScriptMethod.METHOD_DOCKER_CLI)
        check_temp_command = CHECK_TEMP_DIRECTORY.format(prefix=prefix)
        _, check_temp_error = subprocess_popen(
            check_temp_command,
            stderr=subprocess.PIPE,
            shell=True,
        ).communicate()  # && can only work on shell=True

        if check_temp_error:
            raise ScriptError(
                message="Unexpected Error During Getting Temp Directory.",
                error=check_temp_error,
            )

        temp_directory = "/tmp/"
    elif method in [ScriptMethod.METHOD_HOST_CLI, ScriptMethod.METHOD_PYCARDANO]:
        temp_directory = tempfile.gettempdir()

    if temp_directory != "":
        return os.path.join(temp_directory, "")

    raise InvalidMethod(method=method)


def create_file_copy_in_docker_container(source_filename):
    """
    Creates a copy of a file in the docker container

    :param source_filename: name of the file to be copied
    :return: the filename of the copied file in the docker container
    """
    masspayments_settings = get_script_settings()
    source_dir_and_filename = os.path.split(source_filename)
    temp_copy_filename = (
        f"{check_and_create_temp_directory(ScriptMethod.METHOD_DOCKER_CLI)}"
        f"{source_dir_and_filename[1]}"
    )
    copy_command = CREATE_FILE_COPY_TO_DOCKER.format(
        source_filename=source_filename,
        filename=temp_copy_filename,
        prefix=masspayments_settings.command_prefix(ScriptMethod.METHOD_DOCKER_CLI),
    )
    _, copy_command_error = subprocess_popen(
        copy_command,
        stderr=subprocess.PIPE,
        shell=True,
    ).communicate()  # && Works in shell = True
    if copy_command_error:
        raise InvalidFileError(
            message="Unexpected Error Copying File to Docker.",
            error=copy_command_error,
            file=source_filename,
        )

    return temp_copy_filename


def read_file(filename, method=ScriptMethod.METHOD_DOCKER_CLI):
    """
    Reads a file
    :param filename: File to be read
    :param method: method that will be used for reading the file
    :return: File contents
    """
    masspayments_settings = get_script_settings()
    if method in [ScriptMethod.METHOD_DOCKER_CLI, ScriptMethod.METHOD_PYCARDANO]:
        pycardano_context = CACHE_VALUES.get("pycardano_context")
        prefix = masspayments_settings.command_prefix(
            method,
            pycardano_context.command_prefix if pycardano_context else False,
        )
        file_command = READ_FILE.format(prefix=prefix, filename=filename)
        file_content = subprocess_popen(
            file_command.split(),
            stdout=subprocess.PIPE,
        ).stdout.read()

        return file_content.decode("utf-8")
    elif method == ScriptMethod.METHOD_HOST_CLI:
        with open(filename, "r") as file:
            file_content = file.read()
        return file_content

    raise InvalidMethod(method=method)


def get_protocol_parameters(
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    return_file=False,
):
    """
    Get the file containing cardano protocol parameters
    :param network: Network where the function will get the protocol parameters
    :param method: Method that will be used for connecting to cardano
    :param return_file: Boolean If the function should return the protocol file or the detail dictionary
    :return: Filename of the protocol file
    """

    masspayments_settings = get_script_settings()

    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    if not isinstance(return_file, bool):
        raise InvalidType(
            type=type(return_file),
            message="Invalid return file argument type.",
        )

    if method in [ScriptMethod.METHOD_DOCKER_CLI, ScriptMethod.METHOD_HOST_CLI]:
        prefix = masspayments_settings.command_prefix(method)
        network_flag = masspayments_settings.network_flag(network)
        protocol_filename = (
            "mainnet-protocol.json"
            if network == CardanoNetwork.MAINNET
            else "testnet-protocol.json"
        )

        if return_file:
            protocol_command = QUERY_PROTOCOL_PARAMETERS_WITH_FILE.format(
                prefix=prefix,
                network=network_flag,
                protocol_filename=protocol_filename,
            )
            _, protocol_error = subprocess_popen(
                protocol_command.split(),
                stderr=subprocess.PIPE,
            ).communicate()

            if protocol_error:
                raise ScriptError(
                    message="Unexpected Error Protocol Fetch.",
                    error=protocol_error,
                )

            return protocol_filename
        else:
            protocol_command = QUERY_PROTOCOL_PARAMETERS.format(
                prefix=prefix,
                network=network_flag,
            )
            protocol_results = subprocess_popen(
                protocol_command.split(),
                stdout=subprocess.PIPE,
            ).stdout.read()
            protocol_results_str = protocol_results.decode("utf-8")
            protocol_details = json.loads(protocol_results_str)

            return {
                "max_tx_size": protocol_details.get("maxTxSize", 0),
                "min_fee_per_transaction": protocol_details.get("txFeeFixed", 0),
                "fee_per_byte": protocol_details.get("txFeePerByte", 0),
            }
    elif method == ScriptMethod.METHOD_PYCARDANO:
        pycardano_context = CACHE_VALUES.get("pycardano_context")
        protocol_details = pycardano_context.protocol_param
        return {
            "max_tx_size": protocol_details.max_tx_size,
            "min_fee_per_transaction": protocol_details.min_fee_constant,
            "fee_per_byte": protocol_details.min_fee_coefficient,
        }

    raise InvalidMethod(method=method)


def get_latest_slot_number(
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Get latest slot number in blockchain
    :param network: Network where the function will get the latest block details
    :param method: Method that will be used for fetching latest block details
    :return: latest slot number
    """

    masspayments_settings = get_script_settings()

    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
    ]:
        prefix = masspayments_settings.command_prefix(method)
        network_flag = masspayments_settings.network_flag(network)

        tip_query_command = QUERY_TIP.format(prefix=prefix, network=network_flag)
        tip_query_results = subprocess_popen(
            tip_query_command.split(),
            stdout=subprocess.PIPE,
        ).stdout.read()
        tip_query_results_str = tip_query_results.decode("utf-8")
        tip_query_details = json.loads(tip_query_results_str)

        return tip_query_details.get("slot")
    elif method == ScriptMethod.METHOD_PYCARDANO:
        pycardano_context = CACHE_VALUES.get("pycardano_context")
        return pycardano_context.last_block_slot

    raise InvalidMethod(method=method)


def create_transaction_command(
    input_arg,
    output_arg,
    filename,
    prefix="",
    fee=None,
    ttl=None,
    metadata_filename=None,
    is_draft=True,
    reward_details={},
):
    """
    Creates the build cardano transaction command

    :param input_arg: Number of Input UTxO or List of Input UTxO Details (hash, index, amount)
    :param output_arg: Number of Output UTxO or List of Output TX Details (address+amount)
    :param filename: File where the transaction details be stored
    :param prefix: Additional Strings that will be placed before the command
    :param fee: Transaction Fee (Optional)
    :param ttl: Transaction TTL (Optional)
    :param metadata_filename: Name of the Metadata JSON File (Optional)
    :param is_draft: Flag to determine whether the file being created is a draft or not (Optional)
    :param reward_details: Map containing reward details (Optional)

    :return: Build Transaction Command String
    """

    # Transaction Input Details
    tx_in_details = ""
    if isinstance(input_arg, int):
        tx_in_details += (
            "--tx-in 0000000000000000000000000000000000000000000000000000000000000000#1 "
            * input_arg
        )
    elif isinstance(input_arg, list):
        for utxo_detail in input_arg:
            tx_in_details += f"--tx-in {utxo_detail.tx_hash}#{utxo_detail.tx_index} "
    else:
        raise ScriptError(
            message="Invalid input argument type.",
            additional_context={"type": type(input_arg)},
        )

    if not isinstance(filename, str):
        raise ScriptError(
            message="Invalid filename argument type.",
            additional_context={"type": type(filename)},
        )

    if not isinstance(prefix, str):
        raise ScriptError(
            message="Invalid prefix argument type.",
            additional_context={"type": type(prefix)},
        )

    if metadata_filename and not isinstance(metadata_filename, str):
        raise ScriptError(
            message="Invalid metadata filename argument type.",
            additional_context={"type": type(metadata_filename)},
        )

    if not isinstance(is_draft, bool):
        raise ScriptError(
            message="Invalid is draft argument type.",
            additional_context={"type": type(is_draft)},
        )

    if not is_draft:
        if fee is None or not isinstance(fee, (int, str)):
            raise ScriptError(
                message="Invalid Fee argument type.",
                additional_context={"type": type(fee)},
            )

        if ttl is None or not isinstance(ttl, (int, str)):
            raise ScriptError(
                message="Invalid TTL argument type.",
                additional_context={"type": type(ttl)},
            )

    # Transaction Output Details
    tx_out_details = ""
    if isinstance(output_arg, int):
        source_address = CACHE_VALUES.get("source_address", "")
        tx_out_details += f"--tx-out {source_address}+0 " * output_arg
    elif isinstance(output_arg, list):
        for utxo_detail in output_arg:
            utxo_address = utxo_detail.address
            utxo_amount = 0
            if not is_draft:
                utxo_amount = utxo_detail.amount
            tx_out_details += f"--tx-out {utxo_address}+{utxo_amount} "
    else:
        raise ScriptError(
            message="Invalid output argument type.",
            additional_context={"type": type(output_arg)},
        )

    # Extra details
    extra_details = ""
    if isinstance(reward_details, dict) and reward_details != {}:
        if is_draft:
            extra_details += f"--withdrawal {reward_details.get('stake_address')}+0 "
        else:
            extra_details += f"--withdrawal {reward_details.get('stake_address')}+{reward_details.get('stake_amount')} "
    elif not isinstance(reward_details, dict):
        raise ScriptError(
            message="Invalid reward details type.",
            additional_context={"type": type(reward_details)},
        )
    if is_draft:
        extra_details += "--fee 0 --invalid-hereafter 0 "
    else:
        extra_details += f"--fee {fee} --invalid-hereafter {ttl} "

    # Metadata
    if metadata_filename:
        extra_details += f"--metadata-json-file {metadata_filename} "

    tx_command = TRANSACTION_BUILD.format(
        prefix=prefix,
        tx_in_details=tx_in_details,
        tx_out_details=tx_out_details,
        tx_filename=filename,
        extra_details=extra_details,
    )

    return tx_command


def create_transaction_file(
    input_arg,
    output_arg,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    is_draft=True,
    fee=None,
    ttl=None,
    reward_details={},
):
    """
    Creates a transaction draft file

    :param input_arg: Number of Input UTxO or List of Input UTxO Details (hash, index, amount)
    :param output_arg: Number of Output UTxO or List of Output TX Details (address+amount)
    :param method: Method that will be used for creating transaction draft
    :param is_draft: Flag to determine whether the file being created is a draft or not
    :param fee: Transaction Fee (Optional)
    :param ttl: Transaction TTL (Optional)
    :param reward_details: Map containing reward details (Optional)
    :return: Transaction Draft File Name (CLI Methods), Transaction Object Details (Pycardano Method)
    """
    masspayments_settings = get_script_settings()

    if method in [ScriptMethod.METHOD_DOCKER_CLI, ScriptMethod.METHOD_HOST_CLI]:
        # Create transaction draft
        prefix = masspayments_settings.command_prefix(method)
        tx_filename = f"{check_and_create_temp_directory(method)}{uuid.uuid4().hex}."
        tx_filename += "draft" if is_draft else "raw"

        try:
            tx_command = create_transaction_command(
                input_arg=input_arg,
                output_arg=output_arg,
                filename=tx_filename,
                prefix=prefix,
                fee=fee,
                ttl=ttl,
                metadata_filename=CACHE_VALUES.get("metadata_file"),
                is_draft=is_draft,
                reward_details=reward_details,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error During TX File Creation.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during Build TX Command Creation

        _, process_error = subprocess_popen(
            tx_command.split(),
            stderr=subprocess.PIPE,
        ).communicate()

        if process_error:
            raise ScriptError(
                message="Unexpected Error During Transaction Creation.",
                error=process_error,
            )

        return tx_filename
    elif method == ScriptMethod.METHOD_PYCARDANO:
        # Get pycardano context object
        pycardano_context = CACHE_VALUES.get("pycardano_context")
        tx_builder = TransactionBuilder(pycardano_context)

        source_address = CACHE_VALUES.get("source_address", "")

        if isinstance(input_arg, int):
            for _ in range(input_arg):
                tx_builder.add_input(
                    UTxO(
                        input=TransactionInput.from_primitive(
                            [
                                "0000000000000000000000000000000000000000000000000000000000000000",
                                1,
                            ],
                        ),
                        # Fake amount just to handle price coverage
                        output=TransactionOutput.from_primitive(
                            [source_address, 999999999],
                        ),
                    ),
                )
        elif isinstance(input_arg, list):
            for utxo_detail in input_arg:
                tx_builder.add_input(
                    UTxO(
                        input=TransactionInput.from_primitive(
                            [utxo_detail.tx_hash, utxo_detail.tx_index],
                        ),
                        output=TransactionOutput.from_primitive(
                            [utxo_detail.address, utxo_detail.amount],
                        ),
                    ),
                )

        if isinstance(output_arg, int):
            for _ in range(output_arg):
                tx_builder.add_output(
                    TransactionOutput(
                        address=Address.from_primitive(source_address),
                        amount=0,
                    ),
                )
        elif isinstance(output_arg, list):
            for payment_detail in output_arg:
                tx_builder.add_output(
                    TransactionOutput(
                        address=payment_detail.address,
                        amount=payment_detail.amount,
                    ),
                )

        if CACHE_VALUES.get("metadata_file"):
            with open(CACHE_VALUES.get("metadata_file"), "r") as file:
                metadata_content = file.read()
                metadata_details = json.loads(metadata_content)
                # For PyCardano Metadata, Keys should be of integer type
                tx_auxiliary_data = {}
                for key in metadata_details:
                    tx_auxiliary_data[int(key)] = metadata_details[key]
                tx_builder.auxiliary_data = AuxiliaryData(
                    data=AlonzoMetadata(metadata=tx_auxiliary_data),
                )

        if fee:
            tx_builder.fee = fee

        if ttl:
            tx_builder.ttl = ttl

        return {
            "transaction_object": Transaction(
                TransactionBody(
                    inputs=[i.input for i in tx_builder.inputs],
                    outputs=tx_builder.outputs,
                    fee=tx_builder.fee or 0,
                    ttl=tx_builder.ttl or 0,
                    mint=tx_builder.mint,
                    auxiliary_data_hash=tx_builder.auxiliary_data.hash()
                    if tx_builder.auxiliary_data
                    else None,
                    script_data_hash=tx_builder.script_data_hash,
                    required_signers=tx_builder.required_signers or [],
                    validity_start=tx_builder.validity_start,
                    collateral=[c.input for c in tx_builder.collaterals]
                    if tx_builder.collaterals
                    else [],
                ),
                tx_builder._build_fake_witness_set(),
                auxiliary_data=tx_builder.auxiliary_data,
            ),
            "tx_builder": tx_builder,
        }

    raise InvalidMethod(method=method)


def delete_temp_file(filename, method=ScriptMethod.METHOD_DOCKER_CLI):
    """
    Deletes the transaction draft file

    :param filename: Transaction Draft Filename
    :param method: Method that will be used for deleting transaction draft
    :return: True if Delete File succeeds
    """
    masspayments_settings = get_script_settings()
    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
        ScriptMethod.METHOD_PYCARDANO,
    ]:
        prefix = masspayments_settings.command_prefix(method)
        if method == ScriptMethod.METHOD_PYCARDANO:
            if isinstance(filename, dict):
                # This is a transaction object
                return True
            pycardano_context = CACHE_VALUES.get("pycardano_context")
            prefix = pycardano_context.command_prefix
        delete_command = DELETE_FILE.format(prefix=prefix, filename=filename)

        _, delete_error = subprocess_popen(
            delete_command.split(),
            stderr=subprocess.PIPE,
        ).communicate()

        if delete_error:
            raise InvalidFileError(
                message="Unexpected Error During File Deletion.",
                error=delete_error,
                file=filename,
            )

        return True

    raise InvalidMethod(method=method)


def get_tx_size(tx_file, method=ScriptMethod.METHOD_DOCKER_CLI):
    """
    Get Tx Byte Size of a Cardano Transaction File
    :param tx_file: Transaction File Name
    :param method: Method that will be used for checking tx file size
    :return: byte size
    """
    if method == ScriptMethod.METHOD_PYCARDANO and isinstance(tx_file, dict):
        tx_obj = tx_file.get("transaction_object")
        return len(tx_obj.to_cbor("bytes"))

    try:
        tx_content = read_file(filename=tx_file, method=method)
    except ScriptError as e:
        raise e
    except Exception as e:
        raise InvalidFileError(
            message="Unexpected Error Reading TX File.",
            error=e,
            traceback=traceback.format_exc(),
            file=tx_file,
        )  # Error during read transaction draft file

    # Convert content to object
    tx_details = json.loads(tx_content)
    tx_raw = tx_details.get("cborHex", "")
    tx_byte_array = bytearray.fromhex(tx_raw)

    return len(tx_byte_array)


def sign_tx_file(
    tx_file,
    signing_key_files,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    network=CardanoNetwork.TESTNET,
):
    """
    Create a signed transaction file
    :param tx_file: TX File to be signed
    :param signing_key_files: List of Signing Key Files to be used
    :param method: Method that will be used for creating transaction draft
    :param network: Network where the function will get the minimum transaction fee
    :return: TX Signed File
    """
    masspayments_settings = get_script_settings()

    if not isinstance(signing_key_files, list):
        raise InvalidType(
            type=type(signing_key_files),
            message="Invalid signing key file list argument type.",
        )
    if network not in [cn for cn in CardanoNetwork]:
        raise InvalidNetwork(network=network)

    if method in [ScriptMethod.METHOD_DOCKER_CLI, ScriptMethod.METHOD_HOST_CLI]:
        prefix = masspayments_settings.command_prefix(method)
        tx_filename = f"{tx_file}.signed"
        network_flag = masspayments_settings.network_flag(network)

        signing_file_list = signing_key_files
        if method == ScriptMethod.METHOD_DOCKER_CLI:
            signing_file_list = []
            for sign_key_filename in signing_key_files:
                # Create a temporary signing key file
                try:
                    temp_signing_key_filename = create_file_copy_in_docker_container(
                        sign_key_filename,
                    )
                except ScriptError as e:
                    raise e
                except Exception as e:
                    raise InvalidFileError(
                        message="Unexpected Error Creating a temporary copy in Docker Container.",
                        error=e,
                        traceback=traceback.format_exc(),
                        file=sign_key_filename,
                    )
                signing_file_list.append(temp_signing_key_filename)
        signing_file_parameters = [
            f"--signing-key-file {sk_file}" for sk_file in signing_file_list
        ]

        sign_command = TRANSACTION_SIGN.format(
            prefix=prefix,
            raw_file=tx_file,
            network=network_flag,
            signing_key_file_details=" ".join(signing_file_parameters),
            signed_file=tx_filename,
        )
        _, sign_error = subprocess_popen(
            sign_command.split(),
            stderr=subprocess.PIPE,
        ).communicate()  # && Works in shell = True
        if sign_error:
            raise InvalidFileError(
                message="Unexpected Error During Transaction Signing.",
                error=sign_error,
                file=tx_file,
            )

        if method == ScriptMethod.METHOD_DOCKER_CLI:
            # Remove Signing Key Files
            for sk_file in signing_file_list:
                try:
                    delete_temp_file(sk_file, method=method)
                except ScriptError as e:
                    raise e
                except Exception as e:
                    raise InvalidFileError(
                        message="Unexpected Error Deleting Signing Key File.",
                        error=e,
                        traceback=traceback.format_exc(),
                        file=sk_file,
                    )

        return tx_filename
    elif method == ScriptMethod.METHOD_PYCARDANO:
        psk_list = [
            PaymentSigningKey.load(signing_key_file)
            for signing_key_file in signing_key_files
        ]
        tx_builder = tx_file.get("tx_builder")
        tx_object = tx_file.get("transaction_object")
        tx_body = tx_object.transaction_body

        # Sign TX
        witness_set = tx_builder.build_witness_set()
        witness_set.vkey_witnesses = []
        for signing_key in psk_list:
            signature = signing_key.sign(tx_body.hash())
            witness_set.vkey_witnesses.append(
                VerificationKeyWitness(signing_key.to_verification_key(), signature),
            )

        tx_file["tx_builder"] = tx_builder
        tx_file["transaction_object"] = Transaction(
            tx_body,
            witness_set,
            auxiliary_data=tx_builder.auxiliary_data,
        )

        return tx_file

    raise InvalidMethod(method=method)


def get_transaction_byte_size(
    input_arg,
    output_arg,
    reward_details={},
    method=ScriptMethod.METHOD_DOCKER_CLI,
    network=CardanoNetwork.TESTNET,
    signing_key_files=None,
):
    """
    Gets the transaction byte size, given the number of input and output utxo
    :param input_arg: Number of Input UTxO or List of Input UTxO details (hash, index, amount)
    :param output_arg: Number of Output UTxO or List of Output UTxO details (address, amount)
    :param reward_details: Map containing reward details
    :param method: Method that will be used for creating transaction draft
    :param network: Network where the function will get the minimum transaction fee
    :param signing_key_files: List of Signing Key Files that will be used for signing
    :return: Size of the draft transaction in bytes
    """
    signing_key_files = signing_key_files or []

    if isinstance(input_arg, int):
        num_input = input_arg
    elif isinstance(input_arg, list):
        num_input = len(input_arg)
    else:
        raise InvalidType(message="Invalid input argument type.", type=type(input_arg))

    if isinstance(output_arg, int):
        num_output = output_arg
    elif isinstance(output_arg, list):
        num_output = len(output_arg)
    else:
        raise InvalidType(
            message="Invalid output argument type.",
            type=type(output_arg),
        )

    if num_input < 1:
        raise EmptyList(field="Input UTxO List")
    if num_output < 1:
        raise EmptyList(field="Output UTxO List")
    if network not in [cn for cn in CardanoNetwork]:
        raise InvalidNetwork(network=network)
    if not isinstance(signing_key_files, list):
        raise InvalidType(
            type=type(signing_key_files),
            message="Invalid signing key file list argument type.",
        )
    if not isinstance(reward_details, dict):
        raise InvalidType(
            type=type(reward_details),
            message="Invalid reward details type.",
        )

    if method in [ScriptMethod.METHOD_DOCKER_CLI, ScriptMethod.METHOD_HOST_CLI]:
        # Create Draft File
        try:
            draft_file = create_transaction_file(
                input_arg=input_arg,
                output_arg=output_arg,
                method=method,
                reward_details=reward_details,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Creating TX Draft File.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during create transaction draft file

        # Find Fee
        try:
            tx_fee = get_transaction_fee(
                num_input=num_input,
                num_output=num_output,
                draft_file=draft_file,
                network=network,
                method=method,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Getting TX Fee.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during Fee Computation

        # Get Latest Slot Number
        try:
            slot_number = get_latest_slot_number(network=network, method=method)
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Getting Latest Slot Number.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during Slot Number Fetch

        # Create Raw File
        try:
            raw_file = create_transaction_file(
                input_arg=input_arg,
                output_arg=output_arg,
                fee=tx_fee,
                ttl=slot_number,
                method=method,
                is_draft=False,
                reward_details=reward_details,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Creating TX Draft File.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during create transaction draft file

        # Create Signed File
        try:
            if not signing_key_files:
                signing_key_files = CACHE_VALUES.get("source_signing_key_file")
            signed_file = sign_tx_file(
                tx_file=raw_file,
                network=network,
                method=method,
                signing_key_files=signing_key_files,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise InvalidFileError(
                message="Unexpected Error Signing TX File.",
                error=e,
                traceback=traceback.format_exc(),
                file=raw_file,
            )  # Error during transaction signing

        # Get Signed File
        try:
            tx_size = get_tx_size(tx_file=signed_file, method=method)
        except ScriptError as e:
            raise e
        except Exception as e:
            raise InvalidFileError(
                message="Unexpected Error Getting TX File Size.",
                error=e,
                traceback=traceback.format_exc(),
                file=signed_file,
            )  # Error during read transaction draft file

        # Delete Temporary Files
        files_to_delete_list = [draft_file, raw_file, signed_file]
        # Delete Draft File
        for file_to_delete in files_to_delete_list:
            try:
                delete_temp_file(file_to_delete, method)
            except ScriptError as e:
                raise e
            except Exception as e:
                raise InvalidFileError(
                    message="Unexpected Error Deleting Draft TX Files.",
                    error=e,
                    traceback=traceback.format_exc(),
                    file=file_to_delete,
                )  # Error during delete transaction draft file

        return tx_size
    elif method in [ScriptMethod.METHOD_PYCARDANO]:
        pycardano_context = CACHE_VALUES.get("pycardano_context")

        # Get Latest Slot Number
        try:
            tx_ttl = pycardano_context.last_block_slot
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Getting Latest Slot Number.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during Slot Number Fetch

        try:
            tx_details = create_transaction_file(
                input_arg=input_arg,
                output_arg=output_arg,
                method=method,
            )

            tx_obj = tx_details.get("transaction_object")
            tx_builder = tx_details.get("tx_builder")
            tx_body = tx_obj.transaction_body
            tx_body.fee = get_transaction_fee(
                num_input=num_input,
                num_output=num_output,
                draft_file=tx_details,
                network=network,
                method=method,
            )
            tx_body.ttl = tx_ttl
            tx_details["transaction_object"] = Transaction(
                tx_body,
                tx_builder._build_fake_witness_set(),
                auxiliary_data=tx_builder.auxiliary_data,
            )

            # Sign TX
            signed_tx_details = sign_tx_file(
                tx_details,
                signing_key_files,
                method=method,
                network=network,
            )
            signed_tx = signed_tx_details.get("transaction_object")

            tx_size = len(signed_tx.to_cbor("bytes"))
            return tx_size
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Building and Signing TX Details via PyCardano.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during build and sign transaction via pycardano

    raise InvalidMethod(method=method)


def get_transaction_fee(
    num_input,
    num_output,
    draft_file=None,
    num_witness=1,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Gets the minimum transaction fee, given the number of input and output utxo, network used, and method used
    :param num_input: Number of Input UTxO
    :param num_output: Number of Output UTxO
    :param draft_file: Reference Transaction Draft File (Optional)
    :param num_witness: Number of Witness required for transaction
    :param network: Network where the function will get the minimum transaction fee
    :param method: Method that will be used for creating transaction draft
    :return: Minimum transaction fee (in Lovelace)
    """

    masspayments_settings = get_script_settings()

    if draft_file:
        if method in [
            ScriptMethod.METHOD_DOCKER_CLI,
            ScriptMethod.METHOD_HOST_CLI,
        ] and not isinstance(draft_file, str):
            raise InvalidType(message="Invalid draft file type.", type=type(draft_file))
        elif method == ScriptMethod.METHOD_PYCARDANO and not isinstance(
            draft_file,
            dict,
        ):
            raise InvalidType(message="Invalid draft file type.", type=type(draft_file))

    if num_witness and not isinstance(num_witness, int):
        raise InvalidType(
            message="Invalid number of witness value type.",
            type=type(num_witness),
        )

    if num_input < 1:
        raise EmptyList(field="Input UTxO List")
    if num_output < 1:
        raise EmptyList(field="Output UTxO List")
    if num_witness < 1:
        raise EmptyList(field="Witness List")
    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    remove_draft_file = False
    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
        ScriptMethod.METHOD_PYCARDANO,
    ]:
        # Create Draft File
        if draft_file is None:
            remove_draft_file = True
            try:
                draft_file = create_transaction_file(
                    input_arg=num_input,
                    output_arg=num_output,
                    method=method,
                )
            except ScriptError as e:
                raise e
            except Exception as e:
                raise ScriptError(
                    message="Unexpected Error Creating TX Draft File.",
                    error=e,
                    traceback=traceback.format_exc(),
                )  # Error during create transaction draft file

    if method in [ScriptMethod.METHOD_DOCKER_CLI, ScriptMethod.METHOD_HOST_CLI]:
        # Get Protocol File
        try:
            protocol_file = get_protocol_parameters(
                network=network,
                method=method,
                return_file=True,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Getting Protocol Parameters.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during fetch protocol

        prefix = masspayments_settings.command_prefix(method)
        network_flag = masspayments_settings.network_flag(network)

        fee_command = TRANSACTION_FEE.format(
            prefix=prefix,
            draft_file=draft_file,
            num_input=num_input,
            num_output=num_output,
            network=network_flag,
            protocol_file=protocol_file,
            num_witness=num_witness,
        )

        fee_content = subprocess_popen(
            fee_command.split(),
            stdout=subprocess.PIPE,
        ).stdout.read()
        # Format is of b'n Lovelace'
        fee_string = fee_content.decode("utf-8")
        fee = int(fee_string.split()[0])

        # Delete Draft File
        if remove_draft_file:
            try:
                delete_temp_file(draft_file, method)
            except ScriptError as e:
                raise e
            except Exception as e:
                raise InvalidFileError(
                    message="Unexpected Error Deleting Draft TX File.",
                    error=e,
                    traceback=traceback.format_exc(),
                    file=draft_file,
                )  # Error during delete transaction draft file

        return fee
    elif method == ScriptMethod.METHOD_PYCARDANO:
        pycardano_context = CACHE_VALUES.get("pycardano_context")
        tx_builder = draft_file.get("tx_builder")
        draft_tx = draft_file.get("transaction_object")

        plutus_execution_units = ExecutionUnits(0, 0)
        for redeemer in tx_builder.redeemers:
            plutus_execution_units += redeemer.ex_units

        return get_pycardano_fee(
            pycardano_context,
            len(draft_tx.to_cbor("bytes")),
            plutus_execution_units.steps,
            plutus_execution_units.mem,
        )
    raise InvalidMethod(method=method)


def get_total_amount_plus_fee(
    input_arg,
    output_list,
    num_witness=1,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Get the total amount of the transaction with transaction fee
    :param input_arg: Number of Input UTxO or List of Input UTxOs
    :param output_list: List of Output UTxO Details (address + amounts)
    :param num_witness: Number of Witness required for transaction
    :param network: Network where the function will get the minimum transaction fee
    :param method: Method that will be used for creating transaction draft
    :return: Total amount required for the transaction + fee
    """
    if isinstance(input_arg, int):
        num_input = input_arg
    elif isinstance(input_arg, list):
        num_input = len(input_arg)
    else:
        raise InvalidType(message="Invalid input argument type.", type=type(input_arg))

    if not isinstance(output_list, list):
        raise InvalidType(
            message="Invalid output argument type.",
            type=type(output_list),
        )
    if not isinstance(num_witness, int):
        raise InvalidType(
            message="Invalid number of witness value type.",
            type=type(num_witness),
        )

    if num_input < 1:
        raise EmptyList(field="Input UTxO List")
    num_output = len(output_list)
    if num_output < 1:
        raise EmptyList(field="Output UTxO List")
    if num_witness < 1:
        raise EmptyList(field="Witness List")
    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    total_amount = 0
    for utxo_detail in output_list:
        total_amount += utxo_detail.amount

    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
        ScriptMethod.METHOD_PYCARDANO,
    ]:
        # Create Draft File
        try:
            draft_file = create_transaction_file(
                input_arg=input_arg,
                output_arg=output_list,
                method=method,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Creating Draft TX File.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during create transaction draft file

        # Calculate Fee
        try:
            tx_fee = get_transaction_fee(
                num_input=num_input,
                num_output=num_output,
                draft_file=draft_file,
                num_witness=num_witness,
                network=network,
                method=method,
            )
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error Getting TX Fee.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during fee calculation

        # Delete Draft File
        try:
            delete_temp_file(filename=draft_file, method=method)
        except ScriptError as e:
            raise e
        except Exception as e:
            raise InvalidFileError(
                message="Unexpected Error Deleting UTxO File.",
                error=e,
                traceback=traceback.format_exc(),
                file=draft_file,
            )  # Error during delete transaction draft file

        return total_amount, tx_fee

    raise InvalidMethod(method=method)


def get_utxo_extra_details(utxo_extras_map):
    """
    Returns a list of extra utxo values
    :param utxo_extras_map: map of utxo extra details
    :return: a formatted list containing the token and their amount
    """
    extras_list = []
    for token in utxo_extras_map.keys():
        # Convert token to ascii
        token_bytes = bytearray.fromhex(token)
        extras_list.append(
            f"- {utxo_extras_map.get(token)} {token_bytes.decode(encoding='utf-8')}",
        )
    return extras_list


def get_wallet_utxo(
    address,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Returns a list of utxo details of a specific wallet address
    :param address: Wallet Address
    :param network: Network where the function will get Wallet UTxO details
    :param method: Method that will be used for getting Wallet UTxO details
    :return: List of UTxO details
    """

    masspayments_settings = get_script_settings()

    if not isinstance(address, str):
        raise InvalidType(type=type(address), message="Invalid address type.")

    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
        ScriptMethod.METHOD_PYCARDANO,
    ]:
        prefix = masspayments_settings.command_prefix(method)
        if method == ScriptMethod.METHOD_PYCARDANO:
            pycardano_context = CACHE_VALUES.get("pycardano_context")
            prefix = pycardano_context.command_prefix

        network_flag = masspayments_settings.network_flag(network)
        utxo_filename = f"{check_and_create_temp_directory(method)}utxo-{address}.json"
        utxo_command = QUERY_WALLET_UTXO.format(
            prefix=prefix,
            address=address,
            network=network_flag,
            utxo_filename=utxo_filename,
        )

        _, utxo_error = subprocess_popen(
            utxo_command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).communicate()

        if utxo_error:
            raise ScriptError(
                message="Unexpected Error During UTxO Fetch.",
                error=utxo_error,
                additional_context={"address": address},
            )

        try:
            utxo_content = read_file(filename=utxo_filename, method=method)
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error While Getting UTxO File Details.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during read utxo file

        # Delete UTxO File
        try:
            delete_temp_file(filename=utxo_filename, method=method)
        except ScriptError as e:
            raise e
        except Exception as e:
            raise ScriptError(
                message="Unexpected Error While Getting UTxO File Details.",
                error=e,
                traceback=traceback.format_exc(),
            )  # Error during delete transaction draft file

        utxo_content = json.loads(utxo_content)
        utxo_details = []

        # Get UTxO details
        for utxo_key in utxo_content:
            utxo_hash_index = utxo_key.split("#")
            utxo_detail = utxo_content.get(utxo_key)
            value_details = utxo_detail.get("value", {})
            value_keys = set(value_details.keys())
            extra_values_list = []
            if value_keys != {"lovelace"}:
                value_keys.remove("lovelace")
                for policy_id in value_keys:
                    extra_values_list += get_utxo_extra_details(
                        value_details.get(policy_id, {}),
                    )
                extra_values_str = "\n".join(extra_values_list)
                print_to_console(
                    f"Ignoring UTxO {utxo_key} for having these extra values:\n{extra_values_str}",
                    output_format=CACHE_VALUES.get("output_format"),
                )
                continue
            utxo_details.append(
                InputUTXO(
                    address=address,
                    tx_hash=utxo_hash_index[0],
                    tx_index=int(utxo_hash_index[1]),
                    amount=value_details.get("lovelace", 0),
                ),
            )

        return utxo_details

    raise InvalidMethod(method=method)


def get_utxo_hash(
    transaction_file,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Get the utxo hash of a transaction file
    :param transaction_file: File containing the cardano transaction
    :param network: Network where the function will get UTxO details
    :param method: Method that will be used for getting UTxO details
    :return: UTxO hash
    """

    masspayments_settings = get_script_settings()

    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    if not isinstance(transaction_file, str):
        raise InvalidType(
            type=type(transaction_file),
            message="Invalid Transction File Type.",
        )

    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
        ScriptMethod.METHOD_PYCARDANO,
    ]:
        prefix = masspayments_settings.command_prefix(method)
        if method == ScriptMethod.METHOD_PYCARDANO:
            pycardano_context = CACHE_VALUES.get("pycardano_context")
            prefix = pycardano_context.command_prefix

        utxo_command = TRANSACTION_TXID.format(
            prefix=prefix,
            transaction_file=transaction_file,
        )
        utxo_hash_results = subprocess_popen(
            utxo_command.split(),
            stdout=subprocess.PIPE,
        ).stdout.read()
        utxo_hash = utxo_hash_results.decode("utf-8").strip()

        return utxo_hash

    raise InvalidMethod(method=method)


def get_staking_address(
    full_address,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Get the staking address from the full address
    :param full_address: Full Address String
    :param network: Network where the function will get the staking address
    :param method: Method that will be used for getting the staking address
    :return: Staking Address String
    """

    masspayments_settings = get_script_settings()

    if not isinstance(full_address, str):
        raise InvalidType(message="Invalid Full Address Type.", type=type(full_address))
    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
    ]:
        prefix = masspayments_settings.wallet_command_prefix(method)
        if method == ScriptMethod.METHOD_PYCARDANO:
            pycardano_context = CACHE_VALUES.get("pycardano_context")
            prefix = pycardano_context.wallet_command_prefix

        inspect_address_command = (
            INSPECT_ADDRESS_DOCKER_COMMAND.format(
                prefix=prefix,
                full_address=full_address,
            )
            if prefix != ""
            else INSPECT_ADDRESS_COMMAND.format(
                full_address=full_address,
            )
        )
        try:
            inspect_address_results = (
                subprocess_popen(
                    inspect_address_command,
                    stdout=subprocess.PIPE,
                    shell=True,
                )
                .stdout.read()
                .decode("utf-8")
            )
            full_address_details = json.loads(inspect_address_results)
            staking_key_hash = full_address_details.get("stake_key_hash")
        except Exception as e:
            raise ScriptError(
                message="Error during Address Inspection via Cardano CLI.",
                error=e,
                traceback=traceback.format_exc(),
                additional_context={"full_address": full_address},
            )

        # Stake Hash Additional Bytes
        # Stated in https://cardano.stackexchange.com/questions/7055/staking-address-bech32
        staking_key_hash = (
            f"e1{staking_key_hash}"
            if network == CardanoNetwork.MAINNET
            else f"e0{staking_key_hash}"
        )
        staking_address_command = (
            STAKE_ADDRESS_FROM_STAKE_HASH_COMMAND.format(
                prefix=prefix,
                stake_prefix="stake_"
                if network == CardanoNetwork.MAINNET
                else "stake_test",
                stake_hash=staking_key_hash,
            )
            if prefix != ""
            else STAKE_ADDRESS_CONVERT_COMMAND.format(
                stake_prefix="stake_"
                if network == CardanoNetwork.MAINNET
                else "stake_test",
                stake_hash=staking_key_hash,
            )
        )
        try:
            staking_address = (
                subprocess_popen(
                    staking_address_command,
                    stdout=subprocess.PIPE,
                    shell=True,
                )
                .stdout.read()
                .decode("utf-8")
                .strip()
            )
        except Exception as e:
            raise ScriptError(
                message="Error during Stake Address Fetch.",
                error=e,
                traceback=traceback.format_exc(),
                additional_context={"full_address": full_address},
            )

        return staking_address
    elif method == ScriptMethod.METHOD_PYCARDANO:
        full_address_obj = Address.from_primitive(full_address)
        stake_address_obj = Address(
            staking_part=full_address_obj.staking_part,
            network=PycardanoNetwork.TESTNET
            if network == CardanoNetwork.TESTNET
            else PycardanoNetwork.MAINNET,
        )
        return str(stake_address_obj)

    raise InvalidMethod(method=method)


def get_stake_address_balance(
    stake_address,
    network=CardanoNetwork.TESTNET,
    method=ScriptMethod.METHOD_DOCKER_CLI,
):
    """
    Get the total reward balance in stake address
    :param stake_address: Stake Address String
    :param network: Network where the function will get the staking balance
    :param method: Method that will be used for getting the staking balance
    :return: Stake Reward Balance (in Lovelace)
    """

    masspayments_settings = get_script_settings()

    if not isinstance(stake_address, str):
        raise InvalidType(
            message="Invalid Stake Address Type.",
            type=type(stake_address),
        )
    if network not in [CardanoNetwork.MAINNET, CardanoNetwork.TESTNET]:
        raise InvalidNetwork(network=network)

    if method in [
        ScriptMethod.METHOD_DOCKER_CLI,
        ScriptMethod.METHOD_HOST_CLI,
        ScriptMethod.METHOD_PYCARDANO,
    ]:
        prefix = masspayments_settings.command_prefix(method)
        if method == ScriptMethod.METHOD_PYCARDANO:
            pycardano_context = CACHE_VALUES.get("pycardano_context")
            prefix = pycardano_context.command_prefix
        network_flag = masspayments_settings.network_flag(network)

        rewards_command = STAKE_REWARDS_COMMAND.format(
            prefix=prefix,
            address=stake_address,
            network=network_flag,
        )
        try:
            rewards_results = (
                subprocess_popen(
                    rewards_command.split(),
                    stdout=subprocess.PIPE,
                )
                .stdout.read()
                .decode("utf-8")
            )
            rewards_details = json.loads(rewards_results)

            return rewards_details[0].get("rewardAccountBalance")
        except Exception as e:
            raise ScriptError(
                message="Error during Stake Address Balance Fetch.",
                error=e,
                traceback=traceback.format_exc(),
                additional_context={"stake_address": stake_address},
            )

    raise InvalidMethod(method=method)
