
import torch
import torch.nn as nn

print("🤖 Starting Neural Network Initialization...")

# 1. Create Input Data (Tensors)
# Simulating 3 samples with 5 features each
input_data = torch.randn(3, 5) 
print(f"\n📊 Input Tensor (3 samples x 5 features):\n{input_data}")

# 2. Define a Simple Neural Layer (Linear Transformation)
# Maps 5 inputs -> 2 outputs (e.g., classifying into 2 categories)
linear_layer = nn.Linear(in_features=5, out_features=2)

print("\n🧠 Neural Layer Initialized:")
print(f"Weights Shape: {linear_layer.weight.shape}")
print(f"Bias Shape:   {linear_layer.bias.shape}")

# 3. Forward Pass (Compute Output)
# Math: Output = (Input @ Weights.T) + Bias
output = linear_layer(input_data)

print(f"\n✨ Output Tensor (3 samples x 2 outputs):\n{output}")
print("\n✅ Success! Your AI environment is ready to build smart things. 🚀")
