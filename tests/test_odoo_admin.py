import datetime as dt
import importlib.util
import zipfile

import pytest

from conftest import ROOT

spec = importlib.util.spec_from_file_location("odoo_admin", ROOT / "scripts" / "odoo_admin.py")
oa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oa)

ENV = {"ODOO_DB_NAME": "pps_demo", "ODOO_LIVE_DB_NAME": "pps_live"}
NOW = dt.datetime(2026, 11, 24, 12, 0, tzinfo=dt.timezone.utc)


def make_backup(path, with_dump=True):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", "{}")
        if with_dump:
            z.writestr("dump.sql", "-- dump")
        z.writestr("filestore/ab/abc", "x")


def test_live_db_is_never_droppable():
    with pytest.raises(oa.AdminError, match="live system of record"):
        oa.check_droppable("pps_live", oa.protected(ENV))
    oa.check_droppable("pps_demo", oa.protected(ENV))  # the demo is fine


def test_protected_name_follows_settings():
    env = oa.settings({"ODOO_LIVE_DB_NAME": "acme_prod"})
    assert oa.protected(env) == {"acme_prod"}
    with pytest.raises(oa.AdminError):
        oa.check_droppable("acme_prod", oa.protected(env))


@pytest.mark.parametrize("bad", ["pps_demo; drop", "PPS", "", "x" * 70, "a-b"])
def test_drop_rejects_odd_names(bad):
    with pytest.raises(oa.AdminError, match="plain database name"):
        oa.check_droppable(bad, set())


def test_backup_path_is_timestamped_utc(tmp_path):
    assert oa.backup_path("pps_live", NOW, tmp_path).name == "pps_live-20261124T120000Z.zip"


def test_verify_backup(tmp_path):
    good, bad = tmp_path / "good.zip", tmp_path / "bad.zip"
    make_backup(good)
    make_backup(bad, with_dump=False)
    assert oa.verify_backup(good)["filestore_files"] == 1
    with pytest.raises(oa.AdminError, match="dump.sql"):
        oa.verify_backup(bad)
    (tmp_path / "junk.zip").write_text("not a zip")
    with pytest.raises(oa.AdminError, match="not a valid zip"):
        oa.verify_backup(tmp_path / "junk.zip")
    nofs = tmp_path / "nofs.zip"
    with zipfile.ZipFile(nofs, "w") as z:
        z.writestr("manifest.json", "{}")
        z.writestr("dump.sql", "-- dump")
    with pytest.raises(oa.AdminError, match="no filestore"):
        oa.verify_backup(nofs)


def test_nuke_needs_a_fresh_verified_backup(tmp_path):
    assert not oa.has_fresh_backup("pps_live", tmp_path, NOW)  # none yet
    old = oa.backup_path("pps_live", NOW - dt.timedelta(hours=30), tmp_path)
    make_backup(old)
    assert not oa.has_fresh_backup("pps_live", tmp_path, NOW)  # too old
    fresh = oa.backup_path("pps_live", NOW - dt.timedelta(hours=2), tmp_path)
    make_backup(fresh)
    assert oa.has_fresh_backup("pps_live", tmp_path, NOW)
    fresh.write_text("corrupted")
    with pytest.raises(oa.AdminError):
        oa.has_fresh_backup("pps_live", tmp_path, NOW)  # fresh but unreadable: refuse loudly


def test_db_cli_args_put_config_right_after_db():
    assert oa.db_cli_args(["db", "dump", "pps_live", "-"], "/run/c") == ["db", "-c", "/run/c", "dump", "pps_live", "-"]
    with pytest.raises(oa.AdminError):
        oa.db_cli_args(["shell", "-d", "x"], "/run/c")


def test_restore_test_db_is_droppable_but_live_is_not():
    env = oa.settings(ENV)
    oa.check_droppable("pps_live_restore_test", oa.protected(env))
    with pytest.raises(oa.AdminError):
        oa.check_droppable("pps_live", oa.protected(env))
