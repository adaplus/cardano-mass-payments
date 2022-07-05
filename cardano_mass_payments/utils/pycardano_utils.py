import json
import subprocess

from pycardano import ChainContext, Network, ProtocolParameters

from ..constants.commands import QUERY_PROTOCOL_PARAMETERS, QUERY_TIP
from ..constants.common import CardanoNetwork, ScriptMethod
from .common import get_script_settings, subprocess_popen


class CardanoCLIChainContext(ChainContext):
    def __init__(self, cardano_network: CardanoNetwork, use_docker_cli: bool):
        masspayments_settings = get_script_settings()
        self._network = (
            Network.MAINNET
            if cardano_network == CardanoNetwork.MAINNET
            else Network.TESTNET
        )
        self._network_command_flag = masspayments_settings.network_flag(cardano_network)
        self.use_docker_cli = use_docker_cli
        self.command_prefix = masspayments_settings.command_prefix(
            ScriptMethod.METHOD_PYCARDANO,
            use_docker_cli,
        )
        self.wallet_command_prefix = masspayments_settings.wallet_command_prefix(
            ScriptMethod.METHOD_PYCARDANO,
            use_docker_cli,
        )
        self._service_name = "cli"
        self._last_known_block_slot = 0
        self._genesis_param = None
        self._protocol_param = None

    def _check_chain_tip_and_update(self):
        slot = self.last_block_slot
        if self._last_known_block_slot != slot:
            self._last_known_block_slot = slot
            return True
        else:
            return False

    @property
    def protocol_param(self) -> ProtocolParameters:
        """Get current protocol parameters"""
        protocol_command = QUERY_PROTOCOL_PARAMETERS.format(
            prefix=self.command_prefix,
            network=self._network_command_flag,
        )

        if not self._protocol_param or self._check_chain_tip_and_update():
            protocol_results = subprocess_popen(
                protocol_command.split(),
                stdout=subprocess.PIPE,
            ).stdout.read()
            protocol_results_str = protocol_results.decode("utf-8")
            protocol_details = json.loads(protocol_results_str)
            param = ProtocolParameters(
                min_fee_constant=protocol_details.get("txFeeFixed"),
                min_fee_coefficient=protocol_details.get("txFeePerByte"),
                max_block_size=protocol_details.get("maxBlockBodySize"),
                max_tx_size=protocol_details.get("maxTxSize"),
                max_block_header_size=protocol_details.get("maxBlockHeaderSize"),
                key_deposit=protocol_details.get("stakeAddressDeposit"),
                pool_deposit=protocol_details.get("stakePoolDeposit"),
                pool_influence=protocol_details.get("poolPledgeInfluence"),
                monetary_expansion=protocol_details.get("monetaryExpansion"),
                treasury_expansion=protocol_details.get("treasuryCut"),
                decentralization_param=protocol_details.get("decentralization"),
                extra_entropy=protocol_details.get("extraPraosEntropy")
                if protocol_details.get("extraPraosEntropy")
                else "neutral",
                protocol_major_version=protocol_details.get("protocolVersion").get(
                    "major",
                ),
                protocol_minor_version=protocol_details.get("protocolVersion").get(
                    "minor",
                ),
                min_pool_cost=protocol_details.get("minPoolCost"),
                min_utxo=protocol_details.get("minUTxOValue"),
                price_mem=protocol_details.get("executionUnitPrices").get(
                    "priceMemory",
                ),
                price_step=protocol_details.get("executionUnitPrices").get(
                    "priceSteps",
                ),
                max_tx_ex_mem=protocol_details.get("maxTxExecutionUnits").get("memory"),
                max_tx_ex_steps=protocol_details.get("maxTxExecutionUnits").get(
                    "steps",
                ),
                max_block_ex_mem=protocol_details.get("maxBlockExecutionUnits").get(
                    "memory",
                ),
                max_block_ex_steps=protocol_details.get("maxBlockExecutionUnits").get(
                    "steps",
                ),
                max_val_size=protocol_details.get("maxValueSize"),
                collateral_percent=protocol_details.get("collateralPercentage"),
                max_collateral_inputs=protocol_details.get("maxCollateralInputs"),
                coins_per_utxo_word=protocol_details.get("utxoCostPerWord"),
            )
            self._protocol_param = param
        return self._protocol_param

    @property
    def network(self) -> Network:
        """Get current network"""
        return self._network

    @property
    def last_block_slot(self) -> int:
        """Slot number of last block"""
        tip_query_command = QUERY_TIP.format(
            prefix=self.command_prefix,
            network=self._network_command_flag,
        )
        tip_query_results = subprocess_popen(
            tip_query_command.split(),
            stdout=subprocess.PIPE,
        ).stdout.read()
        tip_query_results_str = tip_query_results.decode("utf-8")
        tip_query_details = json.loads(tip_query_results_str)

        return tip_query_details.get("slot")
