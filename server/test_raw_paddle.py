import paddle.inference as paddle_infer
import os

def test_raw_inference():
    model_dir = r"C:\Users\34677\AppData\Local\Temp\paddleocr_models\det"
    model_file = os.path.join(model_dir, "inference.pdmodel")
    params_file = os.path.join(model_dir, "inference.pdiparams")
    
    print(f"Loading model from {model_file}")
    config = paddle_infer.Config(model_file, params_file)
    config.disable_gpu()
    # config.enable_mkldnn() # Disable MKLDNN to see if it's the cause
    
    try:
        predictor = paddle_infer.create_predictor(config)
        print("Predictor created successfully!")
        
        input_names = predictor.get_input_names()
        print(f"Input names: {input_names}")
        
    except Exception as e:
        print(f"Failed to create predictor: {e}")

if __name__ == "__main__":
    test_raw_inference()
