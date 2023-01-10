import yaml


def test_iptables(salt_run_cli, minion):
    """
    Test describe.iptables
    """
    ret = salt_run_cli.run("describe.iptables", tgt=minion.id)
    gen_sls = ret.data["Generated SLS file locations"][0]
    with open(gen_sls) as fp:
        data = yaml.safe_load(fp)
    assert "chain" in data["add_iptables_rule_0"]["iptables.append"][0]
    assert ret.returncode == 0