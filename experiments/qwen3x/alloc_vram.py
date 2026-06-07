import torch

# Set the fraction of total memory to allocate (e.g., 0.5 for 50%)
# Replace 0.5 with your desired fraction (e.g., 0.2 for 20%, 0.9 for 90%)
fraction = 0.5
device_id = 0  # Change if using a different GPU

torch.cuda.set_per_process_memory_fraction(fraction, device_id)
torch.cuda.empty_cache()

# Verify allocation
total_memory = torch.cuda.get_device_properties(device_id).total_memory
allocated_bytes = int(total_memory * fraction)
print(f"Allocated approx {allocated_bytes / 1024**3:.2f} GB")   

import time
time.sleep(300)

