import configparser
import os
import re
import shutil
import subprocess
from io import StringIO
from os import path
from typing import Dict, Optional

ROOT = 'root'
OPTS_BASE = '/opt'
PGPOOL_CONF_DIR = '/etc/pgpool-II'


def config_to_dict(config: configparser.RawConfigParser) -> Dict:
    """
    Convert config object to a dictionary.

    :param config: the config to convert
    :return: the dictionary
    """
    return {
        section: {
            key: value
            for (key, value) in config.items(section)
        } for section in config.sections()
    }


def set_config(
        config: configparser.RawConfigParser, parameters: Dict, prefix: Optional[str] = None,
        index: Optional[int] = None
):
    """
    Set config values from a dictionary.

    :param config: the config object to set values on
    :param parameters: the parameters to set
    :param prefix: the prefix to use if any
    :param index: the index of parameter group if any
    """
    if prefix is not None:
        prefix = f'{prefix}_'
    else:
        prefix = ''
    for key, value in parameters.items():
        config.set(ROOT, prefix + key + (str(index) if index is not None else ''), str(value))


def set_backend_config(config: configparser.RawConfigParser, parameters: Dict, index: int):
    """
    Set the backend config with correct index.

    :param config: the config object to set values on
    :param parameters: the parameters to set
    :param index: the backend server index
    """
    if 'data_directory' not in parameters:
        parameters['data_directory'] = f"'/data/backend_{index}'"
    set_config(config, parameters, 'backend', index)


def build_config():
    """Build the pg-Pool config."""
    config = configparser.RawConfigParser()
    with open('conf/config.template.ini', 'r') as f:
        config.read_string(f'[{ROOT}]\n' + f.read())

    overrides = {}
    config_overrides_path = path.join(OPTS_BASE, 'overrides.ini')
    if os.path.exists(config_overrides_path):
        overrides_config = configparser.RawConfigParser()
        with open(config_overrides_path) as f:
            config.read_string(f'[{ROOT}]\n' + f.read())
        overrides = config_to_dict(overrides_config)['root']

    backends_config = configparser.ConfigParser()
    backends_config.read(path.join(OPTS_BASE, 'backends.ini'))
    backends = config_to_dict(backends_config)

    standby_backend_index = 1

    for backend_type, backend_config in backends.items():
        pgpool_backend_config = {
            'hostname': backend_config['hostname'],
            'port': backend_config['port'],
            'weight': 1,
        }
        if backend_type == 'master':
            pgpool_backend_config['flag'] = "'ALWAYS_MASTER|DISALLOW_TO_FAILOVER'"
            set_backend_config(config, pgpool_backend_config, 0)
            continue

        pgpool_backend_config['flag'] = "'ALLOW_TO_FAILOVER'"
        set_backend_config(config, pgpool_backend_config, standby_backend_index)
        standby_backend_index += 1

    set_config(config, overrides)
    set_config(config, {
        'health_check_user': backends['master']['user'],
        'sr_check_user': backends['master']['user'],
        'pool_passwd': f"'{path.join(PGPOOL_CONF_DIR, 'pool_passwd')}'"
    })

    with StringIO() as file_io:
        config.write(file_io)
        config_file_content = file_io.getvalue()
        config_file_content = re.sub(rf'^\[{ROOT}]\n', '', config_file_content)
        with open(path.join(OPTS_BASE, 'config.ini'), 'w') as f:
            f.write(config_file_content)

    shutil.copy('conf/pool_hba.conf', path.join(PGPOOL_CONF_DIR, 'pool_hba.conf'))
    subprocess.run(['pg_md5', '-m', '-u', backends['master']['user'], backends['master']['password']])


if __name__ == '__main__':
    build_config()
