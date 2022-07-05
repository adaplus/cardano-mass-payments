from .constants.common import CardanoNetwork, ScriptMethod


class MassPaymentsSettings:
    _cardano_node_docker_image_name = "adatest_cardano-testnet-node_1"
    _cardano_wallet_docker_image_name = "adatest_cardano-testnet-wallet_1"
    _cardano_testnet_magic = "1097911063"
    _cardano_minimum_amount = 1000000

    @property
    def cardano_node_docker_image_name(self):
        return self._cardano_node_docker_image_name

    @property
    def cardano_wallet_docker_image_name(self):
        return self._cardano_wallet_docker_image_name

    @property
    def cardano_testnet_magic(self):
        return self._cardano_testnet_magic

    @cardano_testnet_magic.setter
    def cardano_testnet_magic(self, magic_number):
        self._cardano_testnet_magic = str(magic_number)

    @property
    def cardano_minimum_amount(self):
        return self._cardano_minimum_amount

    def command_prefix(self, method, use_docker_cli=False):
        if method == ScriptMethod.METHOD_HOST_CLI:
            return ""
        elif method == ScriptMethod.METHOD_DOCKER_CLI:
            return f"docker exec {self._cardano_node_docker_image_name} "
        elif method == ScriptMethod.METHOD_PYCARDANO:
            return (
                ""
                if not use_docker_cli
                else f"docker exec {self._cardano_node_docker_image_name} "
            )

    def wallet_command_prefix(self, method, use_docker_cli=False):
        if method == ScriptMethod.METHOD_HOST_CLI:
            return ""
        elif method == ScriptMethod.METHOD_DOCKER_CLI:
            return f"docker exec {self._cardano_wallet_docker_image_name} "
        elif method == ScriptMethod.METHOD_PYCARDANO:
            return (
                ""
                if not use_docker_cli
                else f"docker exec {self._cardano_wallet_docker_image_name} "
            )

    def network_flag(self, network):
        return (
            "--mainnet"
            if network == CardanoNetwork.MAINNET
            else f"--testnet-magic {self._cardano_testnet_magic}"
        )
