from lib.logging_config import get_logger, log_context, setup_logging


def test_logging_writes_context_to_file(tmp_path):
    setup_logging("test", log_dir=tmp_path, force=True)
    logger = get_logger("tests")

    with log_context(project_id="project123", run_id="run456", stage="unit"):
        logger.info("hello logging")

    content = (tmp_path / "test.log").read_text(encoding="utf-8")
    assert "hello logging" in content
    assert "project=project123" in content
    assert "run=run456" in content
    assert "stage=unit" in content
