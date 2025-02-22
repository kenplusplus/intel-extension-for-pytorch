#ifdef USE_LIBXSMM
#include "TPPGEMM.h"
#include <torch/all.h>
#include <torch/csrc/autograd/function.h>
#include "tpp/xsmm_functors.h"
namespace torch_ipex {
namespace cpu {

DEFINE_DISPATCH(tpp_linear_nobias_kernel_stub);
DEFINE_DISPATCH(tpp_linear_bias_kernel_stub);
DEFINE_DISPATCH(tpp_linear_gelu_kernel_stub);
DEFINE_DISPATCH(tpp_linear_silu_kernel_stub);
DEFINE_DISPATCH(tpp_linear_relu_kernel_stub);
DEFINE_DISPATCH(tpp_linear_add_kernel_stub);
DEFINE_DISPATCH(tpp_linear_mul_kernel_stub);
DEFINE_DISPATCH(tpp_linear_add_add_kernel_stub);

at::Tensor tpp_linear_nobias_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_wt,
    c10::optional<int64_t> out_features) {
  return tpp_linear_nobias_kernel_stub(kCPU, t_in, t_wt);
}

at::Tensor tpp_linear_bias_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    c10::optional<int64_t> out_features) {
  return tpp_linear_bias_kernel_stub(kCPU, t_in, t_wt, t_bias);
}

at::Tensor tpp_linear_gelu_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    c10::optional<int64_t> out_features) {
  return tpp_linear_gelu_kernel_stub(kCPU, t_in, t_wt, t_bias);
}

at::Tensor tpp_linear_silu_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    c10::optional<int64_t> out_features) {
  return tpp_linear_silu_kernel_stub(kCPU, t_in, t_wt, t_bias);
}

at::Tensor tpp_linear_relu_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    c10::optional<int64_t> out_features) {
  return tpp_linear_relu_kernel_stub(kCPU, t_in, t_wt, t_bias);
}

at::Tensor tpp_linear_add_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_in1,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    double scale,
    c10::optional<int64_t> out_features) {
  return tpp_linear_add_kernel_stub(kCPU, t_in, t_in1, t_wt, t_bias, scale);
}

at::Tensor tpp_linear_mul_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_in1,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    c10::optional<int64_t> out_features) {
  return tpp_linear_mul_kernel_stub(kCPU, t_in, t_in1, t_wt, t_bias);
}

at::Tensor tpp_linear_add_add_forward_cpu(
    at::Tensor& t_in,
    at::Tensor& t_in1,
    at::Tensor& t_in2,
    at::Tensor& t_wt,
    at::Tensor& t_bias,
    double scale,
    c10::optional<int64_t> out_features) {
  return tpp_linear_add_add_kernel_stub(
      kCPU, t_in, t_in1, t_in2, t_wt, t_bias, scale);
}

} // namespace cpu
} // namespace torch_ipex

namespace {

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear(Tensor t_in, Tensor t_wt, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_nobias_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_bias(Tensor t_in, Tensor t_wt, Tensor t_bias, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_bias",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_bias_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_gelu(Tensor t_in, Tensor t_wt, Tensor t_bias, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_gelu",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_gelu_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_add_add(Tensor t_in, Tensor t_in1, Tensor t_in2, Tensor t_wt, Tensor t_bias, float scale, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_add_add",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_add_add_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_relu(Tensor t_in, Tensor t_wt, Tensor t_bias, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_relu",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_relu_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_silu(Tensor t_in, Tensor t_wt, Tensor t_bias, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_silu",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_silu_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_add(Tensor t_in, Tensor t_in1, Tensor t_wt, Tensor t_bias, float scale, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_add",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_add_forward_cpu);
}

TORCH_LIBRARY_FRAGMENT(torch_ipex, m) {
  m.def(
      "tpp_linear_mul(Tensor t_in, Tensor t_in1, Tensor t_wt, Tensor t_bias, int? out_features=None)-> Tensor out");
  m.impl(
      "tpp_linear_mul",
      c10::DispatchKey::CPU,
      torch_ipex::cpu::tpp_linear_mul_forward_cpu);
}

} // namespace
#endif