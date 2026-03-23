from src.ml.training import train_model

def test_training():
    try:
        train_model()
        assert True
    except Exception as e:
        assert False, f"Training failed: {e}"
