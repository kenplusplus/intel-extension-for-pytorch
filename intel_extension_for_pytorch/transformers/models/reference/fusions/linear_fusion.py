import torch
from torch import nn
import math
import copy


class _IPEXlinearSiluRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module

    def forward(self, x):
        return nn.functional.silu(self.linear(x))


class _IPEXlinearAddRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module

    def forward(self, x, y):
        return self.linear(x) + y


class _IPEXlinearAddAddRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module

    def forward(self, x, y, z):
        return self.linear(x) + y + z


class _IPEXlinearMulRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module

    def forward(self, x, y):
        return self.linear(x) * y


class _IPEXlinearNewGeluRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module

    def forward(self, x):
        x = self.linear(x)
        return (
            0.5
            * x
            * (
                1.0
                + torch.tanh(
                    math.sqrt(2.0 / math.pi) * (x + 0.044715 * torch.pow(x, 3.0))
                )
            )
        )


class _IPEXlinearGeluRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module
        self.gelu = nn.GELU()

    def forward(self, x):
        return self.gelu(self.linear(x))


class _IPEXlinearReluRef(nn.Module):
    def __init__(self, module):
        super().__init__()
        self.linear = module

    def forward(self, x):
        return nn.functional.relu(self.linear(x))


class _IPEXConcatLinearRef(nn.Module):
    def __init__(self, linear_list: list):
        super().__init__()
        self.num_concat = len(linear_list)
        for i in range(self.num_concat):
            attr_name = f'linear_{i}'
            setattr(self, attr_name, copy.deepcopy(linear_list[i]))

    def forward(self, x):
        output_list = []
        for i in range(self.num_concat):
            assert hasattr(self, f'linear_{i}')
            linear = getattr(self, f'linear_{i}')
            y = linear(x)
            output_list.append(y)
        return tuple(output_list)

    def extra_repr(self):
        return f'num_concat = {self.num_concat}'
