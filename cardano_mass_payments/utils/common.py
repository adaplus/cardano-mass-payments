import json
import subprocess
from json.decoder import JSONDecodeError

from ..cache import CACHE_VALUES
from ..constants.common import ScriptOutputFormats
from ..constants.exceptions import ScriptError
from ..settings import MassPaymentsSettings


def print_to_console(message, output_format):
    """
    Prints messages to console depending on the output format

    :param message: message to be printed
    :param output_format: Output Format
    :return:
    """
    message_to_print = message
    if isinstance(message_to_print, ScriptError):
        message_to_print = (
            str(message)
            if output_format != ScriptOutputFormats.JSON
            else message.json_str()
        )
    if output_format == ScriptOutputFormats.JSON:
        try:
            json.loads(message_to_print)
        except JSONDecodeError:
            return
    print(message_to_print)
    return


def subprocess_popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    shell=False,
    print_output=False,
):
    """
    Runs a command and waits for the response
    :param command: command message/list
    :param stdout: Subprocess constant that will indicate how the console output be handled
    :param stderr: Subprocess constant that will indicate how errors will be handled
    :param shell: Flag that will determine whether the command will be executed through the shell.
    :param print_output: Flag to determine whether to print the output or not
    :return: command process object if print_output = False
    """
    command_process = subprocess.Popen(
        command,
        stdout=stdout,
        stderr=stderr,
        shell=shell,
    )
    if not print_output:
        return command_process
    while True:
        command_output = command_process.stdout.readline().decode("utf-8")
        if command_output == "" and command_process.poll() is not None:
            break
        if command_output:
            print(command_output.strip())
        command_process.poll()


def get_script_settings():
    """
    Get the current cache Mass Payment Script Settings
    :return: Current Cache Mass Payment Script Setting object
    """
    script_settings = CACHE_VALUES.get("settings")
    if script_settings is None:
        script_settings = MassPaymentsSettings()
        CACHE_VALUES["settings"] = script_settings
    return script_settings
