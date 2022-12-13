"""
Module for building state file

.. versionadded:: 3006

"""
import logging
import sys

import salt.utils.minions  # pylint: disable=import-error
import yaml
from saltext.salt_describe.utils.init import generate_files

__virtualname__ = "describe"


log = logging.getLogger(__name__)


def __virtual__():
    return __virtualname__


def _parse_salt(minion, pkgs, single_state, include_version, pkg_cmd, **kwargs):
    """
    Parse the returned pkg commands and return
    salt data.
    """
    if single_state:
        if include_version:
            _pkgs = [{name: version} for name, version in pkgs.items()]
        else:
            _pkgs = list(pkgs.keys())

        state_contents = {"installed_packages": {"pkg.installed": [{"pkgs": _pkgs}]}}
    else:
        state_contents = {}
        for name, version in pkgs.items():
            state_name = f"install_{name}"
            if include_version:
                state_contents[state_name] = {"pkg.installed": [{"name": name, "version": version}]}
            else:
                state_contents[state_name] = {"pkg.installed": [{"name": name}]}
    return state_contents


def _parse_ansible(minion, pkgs, single_state, include_version, pkg_cmd, **kwargs):
    """
    Parse the returned pkg commands and return
    ansible data.
    """
    state_contents = []
    data = {"tasks": []}
    if not kwargs.get("hosts"):
        log.error(
            "Hosts was not passed. You will need to manually edit the playbook with the hosts entry"
        )
    else:
        data["hosts"] = kwargs.get("hosts")
    if single_state:
        _pkgs = list(pkgs.keys())
        data["tasks"].append(
            {
                "name": f"Package Installaion",
                f"{pkg_cmd}": {
                    "name": _pkgs,
                },
            }
        )
    else:
        for name, version in pkgs.items():
            data_name = f"install_{name}"
            if include_version:
                data["tasks"].append(
                    {
                        "name": f"Install package {name}",
                        f"{pkg_cmd}": {
                            "state": version,
                            "name": name,
                        },
                    }
                )
            else:
                data["tasks"].append(
                    {
                        "name": f"Install package {name}",
                        f"{pkg_cmd}": {
                            "name": name,
                        },
                    }
                )
    state_contents.append(data)
    return state_contents


def _parse_chef(minion, pkgs, single_state, include_version, pkg_cmd, **kwargs):
    """
    Parse the returned pkg commands and return
    chef data.
    """

    _contents = []
    for name, version in pkgs.items():
        pkg_template = f"""package '{name}' do
  action :install
end
"""
        _contents.append(pkg_template)
    return _contents


def pkg(
    tgt, tgt_type="glob", include_version=True, single_state=True, config_system="salt", **kwargs
):
    """
    Gather installed pkgs on minions and build a state file.

    CLI Example:

    .. code-block:: bash

        salt-run describe.pkg minion-tgt

        salt-run describe.pkg minion-tgt config_system=ansible

        salt-run describe.pkg minion-tgt config_system=chef
    """

    ret = __salt__["salt.execute"](
        tgt,
        "pkg.list_pkgs",
        tgt_type=tgt_type,
    )

    for minion in list(ret.keys()):

        _, grains, _ = salt.utils.minions.get_minion_data(minion, __opts__)

        pkg_cmd = None
        if config_system == "ansible":
            if grains["os_family"] not in ("Debian", "RedHat"):
                log.debug("Unsupported minion")
                continue
            else:
                if grains["os_family"] in ("Debian",):
                    pkg_cmd = "apt"
                elif grains["os_family"] in ("RedHat"):
                    pkg_cmd = "dnf"

        pkgs = ret[minion]
        state_contents = getattr(sys.modules[__name__], f"_parse_{config_system}")(
            minion, pkgs, single_state, include_version, pkg_cmd, **kwargs
        )

        if config_system in ("ansible", "salt"):
            state = yaml.dump(state_contents)
        else:
            state = "\n".join(state_contents)
        generate_files(__opts__, minion, state, sls_name="pkg", config_system=config_system)

    return True
