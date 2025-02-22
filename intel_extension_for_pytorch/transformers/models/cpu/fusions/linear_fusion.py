import torch
from torch import nn
import math
import warnings
import copy
from intel_extension_for_pytorch.nn.modules import IpexWoqLinear
from intel_extension_for_pytorch.quantization import get_weight_only_quant_qconfig_mapping

class _IPEXlinearFusionCPU(nn.Module):
    def __init__(self, linear, tpp=False, woq=False):
        super().__init__()
        self.tpp = tpp
        self.woq = woq
        self.dtype = linear.weight.dtype if self.tpp else None

    def extra_repr(self):
        extra_repr_str = f'dtype = {self.dtype}, tpp = {self.tpp}, woq = {self.woq}'
        return extra_repr_str


class _IPEXlinearSiluCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module

    def forward(self, x):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_silu(
                x,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
                self.linear.out_features,
            )
        else:  # fallback path
            return nn.functional.silu(self.linear(x))


class _IPEXlinearReluCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module

    def forward(self, x):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_relu(
                x,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
                self.linear.out_features,
            )
        else:  # fallback path
            return nn.functional.relu(self.linear(x))


class _IPEXlinearMulCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module

    def forward(self, x, y):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            y = y.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_mul(
                x,
                y,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
                self.linear.out_features,
            )
        else:  # fallback path
            return self.linear(x) * y


class _IPEXlinearAddCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module

    def forward(self, x, y):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            y = y.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_add(
                x,
                y,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
                1.0,
                self.linear.out_features,
            )
        if self.woq and hasattr(self.linear, "_op_context") and \
                self.linear._op_context is not None:
            return torch.ops.torch_ipex.woq_linear_add(
                x,
                self.linear._op_context.get_data_handle(),
                [y],
            )
        else:  # fallback path
            return self.linear(x) + y


class _IPEXlinearAddAddCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module

    def forward(self, x, y, z):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            y = y.to(self.dtype).contiguous()
            z = z.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_add_add(
                x,
                y,
                z,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
                1.0,
                self.linear.out_features,
            )
        if self.woq and hasattr(self.linear, "_op_context") and \
                self.linear._op_context is not None:
            return torch.ops.torch_ipex.woq_linear_add_add(
                x,
                self.linear._op_context.get_data_handle(),
                [y, z],
            )
        else:  # fallback path
            return self.linear(x) + y + z


class _IPEXlinearNewGeluCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module

    def forward(self, x):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_gelu(
                x,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
                self.linear.out_features,
            )
        if self.woq and hasattr(self.linear, "_op_context") and \
                self.linear._op_context is not None:
            return torch.ops.torch_ipex.woq_linear_gelu(
                x,
                self.linear._op_context.get_data_handle(),
            )

        else:  # fallback path
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


class _IPEXlinearGeluCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        super().__init__(module, tpp=tpp, woq=woq)
        self.linear = module
        self.gelu = nn.GELU()

    def forward(self, x):
        if self.tpp:
            x = x.to(self.dtype).contiguous()
            return torch.ops.torch_ipex.tpp_linear_gelu(
                x,
                self.linear.weight,
                self.linear.bias if self.linear.bias is not None else x.new_empty(0),
            )
        else:  # fallback path
            x = self.gelu(self.linear(x))
            return x


class _IPEXConcatLinearCPU(_IPEXlinearFusionCPU):
    def __init__(self, module, tpp=False, woq=False):
        assert hasattr(module, 'linear_0')
        super().__init__(module.linear_0, tpp=tpp, woq=woq)
        assert hasattr(module, 'num_concat')
        self.num_concat = module.num_concat
        self.linear_list = []
        for i in range(self.num_concat):
            attr_name = f'linear_{i}'
            assert hasattr(module, attr_name)
            self.linear_list.append(getattr(module, attr_name))
        self.concat_linear = None
        if woq and all(isinstance(linear, IpexWoqLinear) for linear in self.linear_list):
            # Quantization is done before lowering to CPU.
            # We assume weights are all in shape [N, K] and per-channel quantized, axis = 0.
            # And it must be one of the two cases below.
            # Case 1:
            #   - weight dtype = qint8, qscheme = torch.per_channel_affine,
            #   - scales dtype = float, zero points dtype = int
            # Case 2:
            #   - weight dtype = quint4x2, qscheme = torch.per_channel_affine_float_qparams,
            #   - scales dtype = float, zero points dtype = float
            # We need to unpack weights then concat them
            weights_list = []
            scales_list = []
            zeros_list = []
            bias_list = []
            w_dtype = self.linear_list[0].dtype
            lowp_mode = self.linear_list[0]._lowp_mode
            qconfig = get_weight_only_quant_qconfig_mapping(
                weight_dtype=w_dtype, lowp_mode=lowp_mode
            )
            qconfig = qconfig.global_qconfig
            for i in range(self.num_concat):
                linear = self.linear_list[i]
                if not hasattr(linear, '_op_context'):
                    warnings.warn(
                        'Concat linear fusion for CPU WOQ failed '
                        'because linear is not converted to WOQ Linear. '
                        'Falling back to separate linears.'
                    )
                    weights_list = []
                    break
                qw = linear._op_context.to_public(linear._op_context.get_weight())
                if qw.qscheme() not in \
                        [torch.per_channel_affine, torch.per_channel_affine_float_qparams] \
                        or qw.q_per_channel_axis() != 0:
                    warnings.warn(
                        'Concat linear fusion for CPU WOQ failed '
                        'because quantization type of weight is not supported. '
                        'Falling back to separate linears.'
                    )
                    weights_list = []
                    break
                s = qw.q_per_channel_scales().float()
                z = qw.q_per_channel_zero_points().float()
                weights_list.append(qw.dequantize().float())
                scales_list.append(s)
                zeros_list.append(z)
                bias_list.append(linear._op_context.get_bias())
                w_dtype = linear.dtype
            if weights_list:
                concat_weight = torch.concat(weights_list, 0)
                concat_scales = torch.concat(scales_list, -1)
                concat_zeros = torch.concat(zeros_list, -1)
                use_bias = all(bias_list)
                concat_bias = torch.concat(bias_list, 0) if use_bias else None
                mod = nn.Linear(concat_weight.shape[1], concat_weight.shape[0], use_bias)
                mod.weight = nn.Parameter(concat_weight)
                mod.bias = nn.Parameter(concat_bias) if use_bias else None
                mod.qconfig = qconfig
                mod._num_concats = len(weights_list)
                if w_dtype == torch.quint4x2:
                    self.concat_linear = IpexWoqLinear.from_float_and_int4_weight(
                        mod, concat_weight, concat_scales, concat_zeros
                    )
                else:  # qint8
                    assert w_dtype == torch.qint8
                    self.concat_linear = IpexWoqLinear.from_float(mod)
        else:
            for i in range(self.num_concat):
                attr_name = f'linear_{i}'
                setattr(self, attr_name, copy.deepcopy(getattr(module, attr_name)))

    def forward(self, x):
        if self.concat_linear is not None:
            num_concats = self.concat_linear._num_concats
            concat_output = self.concat_linear(x)
            hidden_size = concat_output.shape[-1] // num_concats
            concat_output = concat_output.view(num_concats, -1, hidden_size)
            expected_shape = list(x.shape)[:-1] + [hidden_size]
            return tuple([concat_output[i].view(expected_shape) for i in range(num_concats)])
        output_list = []
        for i in range(self.num_concat):
            assert hasattr(self, f'linear_{i}')
            linear = getattr(self, f'linear_{i}')
            y = linear(x)
            output_list.append(y)
        return tuple(output_list)
