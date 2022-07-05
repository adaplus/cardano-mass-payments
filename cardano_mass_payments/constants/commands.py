from .common import BashColor

# Cardano Commands
TRANSACTION_BUILD = (
    "{prefix}cardano-cli transaction build-raw "
    "{tx_in_details}"
    "{tx_out_details}"
    "{extra_details}"
    "--out-file {tx_filename}"
)
TRANSACTION_FEE = (
    "{prefix}cardano-cli transaction calculate-min-fee "
    "--tx-body-file {draft_file} "
    "--tx-in-count {num_input} "
    "--tx-out-count {num_output} "
    "{network} "
    "--protocol-params-file {protocol_file} "
    "--witness-count {num_witness}"
)
TRANSACTION_TXID = "{prefix}cardano-cli transaction txid --tx-file {transaction_file}"
TRANSACTION_SIGN = (
    "{prefix}cardano-cli transaction sign "
    "--tx-body-file {raw_file} "
    "{signing_key_file_details} "
    "{network} --out-file {signed_file}"
)
TRANSACTION_SUBMIT = (
    "{prefix}cardano-cli transaction submit --tx-file {signed_file} {network}"
)

QUERY_PROTOCOL_PARAMETERS = "{prefix}cardano-cli query protocol-parameters {network}"
QUERY_PROTOCOL_PARAMETERS_WITH_FILE = (
    QUERY_PROTOCOL_PARAMETERS + " --out-file {protocol_filename}"
)
QUERY_TIP = "{prefix}cardano-cli query tip {network}"
QUERY_WALLET_UTXO_VIA_TXID = (
    "{prefix}cardano-cli query utxo --tx-in {tx_hash}#{tx_index} {network}"
)
QUERY_WALLET_UTXO_NO_FILE = (
    "{prefix}cardano-cli query utxo --address {address} {network}"
)
QUERY_WALLET_UTXO = f"{QUERY_WALLET_UTXO_NO_FILE} --out-file {{utxo_filename}}"

# File commands
CHECK_TEMP_DIRECTORY = "{prefix}test ! -d '/tmp' && mkdir '/tmp'"
READ_FILE = "{prefix}cat {filename}"
DELETE_FILE = "{prefix}rm {filename}"

CREATE_FILE_COPY_TO_DOCKER = (
    "sk=$(cat {source_filename}) && {prefix} /bin/bash -c "
    "\"echo '$sk' > {filename}\" && unset sk"
)

# Script commands
STATUS_MESSAGE_SETUP = f"""
success_str="{BashColor.BOLD_GREEN.value}SUCCESS{BashColor.NO_COLOR.value}"
ongoing_str="{BashColor.BOLD_YELLOW.value}ONGOING{BashColor.NO_COLOR.value}"
ttl_expired_str="{BashColor.BOLD_RED.value}TTL EXPIRED{BashColor.NO_COLOR.value}"
"""

FIND_PYTHON_FUNCTION = """

find_valid_python_version () {
    python_str=$(echo $(which python3))
    if ! [[ $python_str ]] ; then
        python_str=$(echo $(which python))
    fi
    echo $python_str
}

python_exec_str=$(find_valid_python_version)
if ! [[ $python_exec_str ]] ; then
    echo "No python version found."
    exit 1
fi
"""

LATEST_SLOT_NUMBER_BASH_FUNCTION = """
get_latest_slot_no () {{
    {tip_query} | {python_exec_str} -c "import sys, json; print(json.load(sys.stdin)['slot'])"
}}
"""

UPDATE_TRANSACTION_PLAN_PYTHON_COMMANDS = ";".join(
    [
        "import json",
        "f = open('{transaction_plan_filename}', 'r+')",
        "data = json.loads(f.read())",
        "{python_update_command}",
        "f.seek(0)",
        "f.write(json.dumps(data))",
        "f.truncate()," "f.close()",
    ],
)

UPDATE_TRANSACTION_PLAN_FILE = (
    f'{{python_exec_str}} -c "{UPDATE_TRANSACTION_PLAN_PYTHON_COMMANDS}"'
)

DUST_TX_SUBMIT_SCRIPT = """
echo "Submitting Dust Transactions to Cardano"

dust_submit_function () {{
    straight_to_polling=${{{polling_arg_index}:-false}}
    if [[ $straight_to_polling == false ]] ; then
        dust_submit_result=$({dust_submit_command})
    else
        dust_submit_result=true
    fi
    if [[ $dust_submit_result ]] ; then
        {ongoing_status_command}
        dust_results=$({utxo_query_command})
        echo -en "Status ${function_index_txid} = $ongoing_str"
        dust_status=$ongoing_str
        until [[ $dust_results == *${function_index_txid}* ]] || [[ $dust_status != "$ongoing_str" ]]
        do
            dust_results=$({utxo_query_command})
            latest_slot=$(get_latest_slot_no)
            if (( $latest_slot > {ttl} )) ; then
                dust_status=$ttl_expired_str
                {expired_status_command}
            fi
        done
        if [[ $dust_status == "$ongoing_str" ]] ; then
            dust_status=$success_str
            {success_status_command}
        fi
        echo -en "\\r\\033[KStatus ${function_index_txid} = $dust_status"
        echo
        if [[ $dust_status != "$success_str" ]] ; then
            exit 1
        fi
    else
        echo "There was an error when the Dust Transaction was submitted to Cardano"
        exit 1
    fi
}}
"""

DUST_SUBMIT_FUNCTION_CALL = (
    "dust_submit_function {signed_file_name} {target_address} {txid_variable_name} "
    "{map_index} {straight_to_poll}"
)

POST_PREP_TX_SUBMIT_SCRIPT = """
echo "Submitting Signed Preparation Transaction to Cardano"

prep_submit_result=$({prep_submit_command})
if [[ $prep_submit_result ]] ; then
    {ongoing_status_command}
    utxo_results=$({utxo_query_command})
    echo -en "Status ${prep_txid_variable} = $ongoing_str"
    prep_status=$ongoing_str
    until [[ $utxo_results == *${prep_txid_variable}* ]] || [[ $prep_status != "$ongoing_str" ]]
    do
        utxo_results=$({utxo_query_command})
        latest_slot=$(get_latest_slot_no)
        if (( $latest_slot > {ttl} )) ; then
            prep_status=$ttl_expired_str
            {expired_status_command}
        fi
    done
    if [[ $prep_status == "$ongoing_str" ]] ; then
        prep_status=$success_str
        {success_status_command}
    fi
    echo -en "\\r\\033[KStatus ${prep_txid_variable} = $prep_status"
    echo
    if [[ $prep_status == "$success_str" ]] ; then
        echo "Preparation Transaction Submission Done"
    else
        exit 1
    fi
else
    echo "There was an error when the Preparation Transaction was submitted to Cardano"
    exit 1
fi
"""

GROUP_TX_ONGOING_SET_FUNCTION_SCRIPT = """
set_group_tx_to_ongoing() {{
    {ongoing_status_command}
}}
"""

GROUP_TX_ONGOING_FUNCTION_CALL = "set_group_tx_to_ongoing {group_tx_index} {txid}"

TX_STATUS_SCRIPT = """
utxo_status_array=({utxo_status_bash_array_str})
array_length=${{#utxo_status_array[@]}}

group_txid_array=()
group_index_array=({utxo_index_array_str})
for (( i=0; i<${{array_length}}; i++ ))
do
    group_index=${{group_index_array[$i]}}
    group_txid_array+=($({transaction_txid_query}))
done

while [[ " ${{utxo_status_array[*]}} " =~ " $ongoing_str " ]]
do
    latest_slot=$(get_latest_slot_no)
    for (( i=0; i<${{array_length}}; i++ ))
    do
        group_txid=${{group_txid_array[$i]}}
        group_index=${{group_index_array[$i]}}
        echo -e "\\033[KStatus $group_txid = ${{utxo_status_array[$i]}}"
        if [[ ${{utxo_status_array[$i]}} == "$ongoing_str" ]] ; then
            group_utxo_results=$({utxo_query_command})
            if [[ $group_utxo_results != *${prep_txid_variable}* ]] ; then
                utxo_status_array[$i]=$success_str
                {success_status_command}
            elif (( $latest_slot > {ttl} )) ; then
                utxo_status_array[$i]=$ttl_expired_str
                {expired_status_command}
            fi
        fi
    done
    echo -en "\\r\\033[${{array_length}}A"
    sleep 1
done
for (( i=0; i<${{array_length}}; i++ ))
do
    group_txid=${{group_txid_array[$i]}}
    echo -e "\\033[KStatus $group_txid = ${{utxo_status_array[$i]}}"
done
echo "Group Transaction Submission Checking Done"
"""

INSPECT_ADDRESS_COMMAND = "echo '{full_address}' | cardano-address address inspect"

INSPECT_ADDRESS_DOCKER_COMMAND = f'{{prefix}}sh -c "{INSPECT_ADDRESS_COMMAND}"'


STAKE_ADDRESS_CONVERT_COMMAND = "bech32 {stake_prefix} <<< {stake_hash}"

STAKE_ADDRESS_FROM_STAKE_HASH_COMMAND = (
    f'{{prefix}}sh -c "{STAKE_ADDRESS_CONVERT_COMMAND}"'
)

STAKE_REWARDS_COMMAND = (
    "{prefix}cardano-cli query stake-address-info --address {address} {network}"
)
