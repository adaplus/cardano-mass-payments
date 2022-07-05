import enum
import json
import uuid

from .constants.common import (
    CardanoNetwork,
    DustCollectionMethod,
    ScriptMethod,
    TransactionStatus,
)


class TransactionPlanEncoder(json.JSONEncoder):
    """
    JSON Encoder for Transaction Plan Objects
    """

    def default(self, o):
        if isinstance(o, enum.Enum):
            return o.value
        return o.__dict__


class InputUTXO:
    """
    Class for Transaction Input UTxO Details

    :param address: Source Address of the Input UTxO
    :param tx_hash: Hash String of the Input UTxO
    :param tx_index: Index of the Input UTxO
    :param amount: Input UTxO Amount in Lovelace
    :param dust_collected_utxo: Flag whether the Input UTxO is created via dust collection
    """

    def __init__(self, address, tx_hash, tx_index, amount, dust_collected_utxo=False):
        self.address = address
        self.tx_hash = tx_hash
        self.tx_index = tx_index
        self.amount = amount
        self.dust_collected_utxo = dust_collected_utxo


class PaymentDetail:
    """
    Class for Transaction Payment Details

    :param address: Target Address
    :param amount: Payment Amount in Lovelace
    """

    def __init__(self, address, amount):
        self.address = address
        self.amount = amount


class PreparationDetail:
    """
    Class for Preparation Transaction Details

    :param prep_input: List of Preparation Transaction Input UTxOs
    :param prep_output: List of Preparation Transaction Payment Details
    :param submission_status: Preparation Transaction submission status
    :param tx_hash_id: Hash String of the Preparation Transaction
    :param withdrawal_amount: Withdrawal Amount in Lovelace
    """

    def __init__(
        self,
        prep_input,
        prep_output,
        submission_status=None,
        tx_hash_id="",
        reward_details={},
    ):
        self.prep_input = prep_input
        self.prep_output = prep_output
        self.reward_details = reward_details
        self.submission_status = (
            submission_status or TransactionStatus.NOT_YET_SUBMITTED
        )
        self.tx_hash_id = tx_hash_id


class PaymentGroup:
    """
    Class for Payment Group Details

    :param index: Payment Group Index
    :param payment_details: List of Payment Details included in this group
    :param amount: Payment Group Total Amount
    :param fee: Payment Group Transaction Fee
    :param tx_size: Payment Group Transaction Size in Bytes
    :param submission_status: Payment Group submission status
    :param tx_hash_id: Hash String of the Payment Group Transaction
    """

    def __init__(
        self,
        index,
        payment_details=None,
        amount=None,
        fee=None,
        tx_size=None,
        submission_status=None,
        tx_hash_id="",
    ):
        self.payment_details = payment_details or []
        self.amount = amount or 0
        self.fee = fee or 0
        self.tx_size = tx_size or 0
        self.index = index
        self.submission_status = (
            submission_status or TransactionStatus.NOT_YET_SUBMITTED
        )
        self.tx_hash_id = tx_hash_id


class SourceAddressDetail:
    """
    Class for Source Address Detail

    :param address: Address String
    :param signing_key_file: Filename of the Corresponding Signing Key File
    :param is_main_source_address: Flag whether the address is the main source address or not
    """

    def __init__(self, address, signing_key_file, is_main_source_address=False):
        self.address = address
        self.signing_key_file = signing_key_file
        self.is_main_source_address = is_main_source_address


class TransactionPlan:
    """
    Class for Transaction Plan Details

    :param prep_detail: Preparation Transaction Details
    :param group_details: List of Payment Group Details
    :param network: Network where the script connects to
    :param script_method: Method used in the script logic
    :param allowed_ttl_slots: Number of slots allowed before the transaction to be deemed invalid
    :param add_change_to_fee: Flag on whether the small change be added to transaction fee or not
    :param filename: Name of the File where the transaction plan be stored
    :param dust_collection_method: Method used for dust collection
    :param dust_collection_threshold: Maximum amount that will be the basis for dust collection
    :param dust_group_details: Map containing the Dust Group Details
    :param source_details: Map containing the source address + signing key file details
    :param metadata: Metadata Details
    :param uuid_str: Transction Plan UUID String
    """

    def __init__(
        self,
        prep_detail,
        group_details,
        network,
        script_method,
        allowed_ttl_slots,
        add_change_to_fee,
        filename=None,
        dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE,
        dust_collection_threshold=10000000,
        dust_group_details=None,
        source_details=None,
        metadata=None,
        uuid_str=None,
    ):
        self.uuid = (
            uuid_str or uuid.uuid4().hex
        )  # All tx files will be associated with this uuid
        self.prep_detail = prep_detail
        self.group_details = group_details
        self.metadata = metadata
        self.network = network
        self.script_method = script_method
        self.allowed_ttl_slots = allowed_ttl_slots
        self.source_details = source_details
        self.add_change_to_fee = add_change_to_fee
        self.dust_group_details = dust_group_details or {}
        self.dust_collection_method = dust_collection_method
        self.dust_collection_threshold = dust_collection_threshold
        self.filename = filename or f"{self.uuid}_transaction_plan.json"

    @classmethod
    def from_transaction_plan_file(cls, transaction_plan_filename):
        """
        Generates a TransactionPlan object from the transaction plan file

        :param transaction_plan_filename: Name of the Transaction plan file
        :return: TransctionPlan object containing details from the transaction plan file
        """
        with open(transaction_plan_filename, "r") as transaction_plan_file:
            transaction_plan_details = json.loads(transaction_plan_file.read())
            prep_details = transaction_plan_details.get("prep_detail", {})

            transaction_plan = cls(
                uuid_str=transaction_plan_details.get("uuid"),
                prep_detail=PreparationDetail(
                    prep_input=[
                        InputUTXO(
                            address=prep_input.get("address"),
                            tx_hash=prep_input.get("tx_hash"),
                            tx_index=prep_input.get("tx_index"),
                            amount=prep_input.get("amount"),
                            dust_collected_utxo=prep_input.get("dust_collected_utxo"),
                        )
                        for prep_input in prep_details.get("prep_input", [])
                    ],
                    prep_output=[
                        PaymentDetail(
                            address=prep_output.get("address"),
                            amount=prep_output.get("amount"),
                        )
                        for prep_output in prep_details.get("prep_output", [])
                    ],
                    submission_status=TransactionStatus(
                        prep_details.get("submission_status"),
                    ),
                    tx_hash_id=prep_details.get("tx_hash_id"),
                    reward_details=prep_details.get("reward_details", {}),
                ),
                group_details=[
                    PaymentGroup(
                        index=payment_group.get("index"),
                        payment_details=[
                            PaymentDetail(
                                address=group_payment.get("address"),
                                amount=group_payment.get("amount"),
                            )
                            for group_payment in payment_group.get(
                                "payment_details",
                                [],
                            )
                        ],
                        amount=payment_group.get("amount"),
                        fee=payment_group.get("fee"),
                        tx_size=payment_group.get("tx_size"),
                        submission_status=TransactionStatus(
                            payment_group.get("submission_status"),
                        ),
                        tx_hash_id=payment_group.get("tx_hash_id"),
                    )
                    for payment_group in transaction_plan_details.get(
                        "group_details",
                        [],
                    )
                ],
                metadata=transaction_plan_details.get("metadata"),
                network=CardanoNetwork(transaction_plan_details.get("network")),
                script_method=ScriptMethod(
                    transaction_plan_details.get("script_method"),
                ),
                allowed_ttl_slots=transaction_plan_details.get("allowed_ttl_slots"),
                source_details=[
                    SourceAddressDetail(
                        address=source_detail.get("address"),
                        signing_key_file=source_detail.get("signing_key_file"),
                        is_main_source_address=source_detail.get(
                            "is_main_source_address",
                        ),
                    )
                    for source_detail in transaction_plan_details.get("source_details")
                ],
                add_change_to_fee=transaction_plan_details.get("add_change_to_fee"),
                dust_collection_method=DustCollectionMethod(
                    transaction_plan_details.get("dust_collection_method"),
                ),
                dust_collection_threshold=transaction_plan_details.get(
                    "dust_collection_threshold",
                ),
                filename=transaction_plan_filename,
            )

        if transaction_plan_details.get("dust_group_details"):
            dust_group_details = transaction_plan_details.get("dust_group_details")
            transaction_plan.dust_group_details = {}
            for target_address in dust_group_details:
                formatted_dust_group_details = [
                    PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=dust_input_detail.get("address"),
                                tx_hash=dust_input_detail.get("tx_hash"),
                                tx_index=dust_input_detail.get("tx_index"),
                                amount=dust_input_detail.get("amount"),
                                dust_collected_utxo=dust_input_detail.get(
                                    "dust_collected_utxo",
                                ),
                            )
                            for dust_input_detail in dust_prep_detail.get("prep_input")
                        ],
                        prep_output=[
                            PaymentDetail(
                                address=dust_payment_detail.get("address"),
                                amount=dust_payment_detail.get("amount"),
                            )
                            for dust_payment_detail in dust_prep_detail.get(
                                "prep_output",
                            )
                        ],
                        submission_status=TransactionStatus(
                            dust_prep_detail.get("submission_status"),
                        ),
                        tx_hash_id=dust_prep_detail.get("tx_hash_id"),
                    )
                    for dust_prep_detail in dust_group_details.get(target_address)
                ]
                transaction_plan.dust_group_details[
                    target_address
                ] = formatted_dust_group_details

        return transaction_plan

    def json(self):
        """
        Generates the JSON String of the Transaction Plan
        :return: JSON String of the Transaction Plan
        """
        return TransactionPlanEncoder().encode(self)

    def general_transaction_details(self):
        """
        Generates the General Transaction Details of the Transaction Plan
        :return: String containing the following details
            - Transaction File Name
            - Number of Dust Transactions Generated
            - Number of Transaction Groups Generated
            - Total Amount To Be Used
            - Expected Maximum Change Return
        """

        # Count Dust Groups Created
        dust_tx_count = 0
        total_input_tx_amount = 0
        tx_group_count = 0
        for target_address in self.dust_group_details:
            for dust_group_detail in self.dust_group_details[target_address]:
                dust_input_list = dust_group_detail.prep_input
                total_input_tx_amount += sum(
                    [
                        dust_input.amount
                        for dust_input in dust_input_list
                        if not dust_input.dust_collected_utxo
                    ],
                )
                if dust_group_detail.submission_status in [
                    TransactionStatus.NOT_YET_SUBMITTED,
                    TransactionStatus.TTL_EXPIRED,
                ]:
                    dust_tx_count += 1

        for tx_group in self.group_details:
            if tx_group.submission_status in [
                TransactionStatus.NOT_YET_SUBMITTED,
                TransactionStatus.TTL_EXPIRED,
            ]:
                tx_group_count += 1

        total_input_tx_amount += sum(
            [
                prep_input.amount
                for prep_input in self.prep_detail.prep_input
                if not prep_input.dust_collected_utxo
            ],
        )

        total_payment_amount = sum(
            [
                prep_output.amount
                for prep_output in self.prep_detail.prep_output
                if isinstance(prep_output.amount, int)
            ],
        )

        return (
            f"Transaction File Name: {self.filename}\n"
            f"Number of Dust Transactions Generated: {dust_tx_count}\n"
            f"Number of Transaction Groups Generated (Excluding preparation Transaction)"
            f": {tx_group_count}\n"
            f"Total Amount To Be Used: {total_input_tx_amount} Lovelace\n"
            f"Expected Maximum Change Return: {total_input_tx_amount - total_payment_amount} Lovelace"
        )
