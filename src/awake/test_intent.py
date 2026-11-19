from awake.intent import match_intent, named_music_query


def test_longest_beats_halt():
    hit = match_intent("停止播放音乐")
    assert hit is not None
    assert hit.name == "music_stop"


def test_halt():
    hit = match_intent("赶紧停下")
    assert hit is not None
    assert hit.name == "halt"


def test_exit():
    hit = match_intent("先这样吧")
    assert hit is not None
    assert hit.name == "exit"


def test_photo_fun():
    hit = match_intent("帮我拍一张")
    assert hit is not None
    assert hit.name == "photo"
    assert hit.category == "娱乐控制"


def test_music_random():
    hit = match_intent("随机播放")
    assert hit is not None
    assert hit.name == "music_random"


def test_named_query():
    assert "青花瓷" in named_music_query("放一首青花瓷")
    hit = match_intent("播放青花瓷")
    assert hit is not None
    assert hit.name == "music_named"


def test_unmute_beats_mute():
    hit = match_intent("取消静音")
    assert hit is not None
    assert hit.name == "volume_unmute"


def test_time_over_alarm():
    hit = match_intent("现在几点")
    assert hit is not None
    assert hit.name == "time"


def test_volume_colloquial():
    hit = match_intent("把音量调大一点")
    assert hit is not None
    assert hit.name == "volume_up"


def test_music_play_dian():
    hit = match_intent("那你放点音乐吧")
    assert hit is not None
    assert hit.name == "music_play"


def test_music_stop_variants():
    hit = match_intent("停止音乐")
    assert hit is not None
    assert hit.name == "music_stop"
