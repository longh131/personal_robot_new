from awake.scheduler import (
    add_job,
    cancel_kind,
    parse_duration_s,
    parse_remind_message,
    pop_due,
)


def test_parse_seconds():
    assert parse_duration_s("倒计时30秒") == 30
    assert parse_duration_s("倒计时十秒") == 10
    assert parse_duration_s("两分钟") == 120
    assert parse_duration_s("半分钟") == 30


def test_parse_remind_msg():
    assert "喝水" in parse_remind_message("五分钟后提醒我喝水")


def test_job_due(monkeypatch):
    cancel_kind(None)
    job = add_job("countdown", 1.0, "时间到")
    assert job.id
    # force due
    job.fire_at = 0
    due = pop_due()
    assert len(due) == 1
    assert due[0].message == "时间到"
