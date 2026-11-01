// Copyright 2026 Yurun Zi
// SPDX-License-Identifier: GPL-3.0-only
//
// The Python form of film_tables.hpp, for the lab. This file only checks and converts arrays; it has no part of the model.
#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <string>

#include "film_tables.hpp"

namespace nb = nanobind;
namespace ft = alcedo::film_tables;

namespace {

using Doubles = nb::ndarray<const double, nb::c_contig, nb::device::cpu>;
using Int64s = nb::ndarray<const int64_t, nb::c_contig, nb::device::cpu>;
using Bytes = nb::ndarray<const uint8_t, nb::c_contig, nb::device::cpu>;

template <class Array>
void RequireShape(const Array& array, const char* name, std::initializer_list<int64_t> shape) {
  bool same = array.ndim() == shape.size();
  size_t axis = 0;
  for (int64_t size : shape) {
    if (same && size >= 0 && static_cast<int64_t>(array.shape(axis)) != size) same = false;
    ++axis;
  }
  if (!same) throw nb::value_error((std::string(name) + ": unexpected array shape").c_str());
}

template <class T>
nb::ndarray<nb::numpy, T> NewArray(std::initializer_list<size_t> shape) {
  size_t size = 1;
  for (size_t value : shape) size *= value;
  T* data = new T[size];
  nb::capsule owner(data, [](void* pointer) noexcept { delete[] static_cast<T*>(pointer); });
  return nb::ndarray<nb::numpy, T>(data, shape, owner);
}

ft::SpectralBand Band(const Doubles& base, const Doubles& dyes, const Doubles& weights, const char* name) {
  const int64_t n = static_cast<int64_t>(base.shape(0));
  RequireShape(base, name, {n});
  RequireShape(dyes, name, {3, n});
  RequireShape(weights, name, {3, n});
  return {n, base.data(), dyes.data(), weights.data()};
}

}  // namespace

NB_MODULE(alcedo_film_tables, m) {
  m.doc() = "Construction of the spectral tables of the film model (step P7). See film_tables.hpp.";

  m.def("log10_band_response", [](Doubles base, Doubles dyes, Doubles weights, Doubles amounts) {
    const ft::SpectralBand band = Band(base, dyes, weights, "band");
    RequireShape(amounts, "amounts", {-1, 3});
    const size_t count = amounts.shape(0);
    auto out = NewArray<double>({count, size_t{3}});
    {
      nb::gil_scoped_release release;
      ft::Log10BandResponse(band, amounts.data(), static_cast<int64_t>(count), out.data());
    }
    return out;
  }, nb::arg("base"), nb::arg("dyes"), nb::arg("weights"), nb::arg("amounts"));

  m.def("solve_dye_amounts", [](Doubles base, Doubles dyes, Doubles weights, Doubles targets, int iterations, double reached_limit) {
    const ft::SpectralBand band = Band(base, dyes, weights, "status");
    RequireShape(targets, "targets", {-1, 3});
    const size_t count = targets.shape(0);
    auto amounts = NewArray<double>({count, size_t{3}});
    int64_t not_reached = 0;
    {
      nb::gil_scoped_release release;
      not_reached = ft::SolveDyeAmounts(band, targets.data(), static_cast<int64_t>(count), iterations, reached_limit, amounts.data());
    }
    return nb::make_tuple(amounts, not_reached);
  }, nb::arg("base"), nb::arg("dyes"), nb::arg("weights"), nb::arg("targets"), nb::arg("iterations"), nb::arg("reached_limit"));

  m.def("build_paper_table", [](Doubles status_base, Doubles status_dyes, Doubles status_weights, Doubles view_base, Doubles view_dyes, Doubles view_weights,
                                double xyz_scale, Doubles axis_start, Doubles axis_range, double axis_power, int64_t nodes, int iterations, double reached_limit) {
    const ft::SpectralBand status = Band(status_base, status_dyes, status_weights, "status");
    const ft::SpectralBand viewing = Band(view_base, view_dyes, view_weights, "viewing");
    RequireShape(axis_start, "axis_start", {3});
    RequireShape(axis_range, "axis_range", {3});
    if (nodes < 2) throw nb::value_error("nodes: the table needs at least 2 nodes per axis");
    const size_t n = static_cast<size_t>(nodes);
    auto table = NewArray<double>({n, n, n, size_t{3}});
    auto not_reached = NewArray<uint8_t>({n, n, n});
    {
      nb::gil_scoped_release release;
      ft::BuildPaperTable(status, viewing, xyz_scale, {nodes, axis_start.data(), axis_range.data(), axis_power}, iterations, reached_limit, table.data(), not_reached.data());
    }
    return nb::make_tuple(table, not_reached);
  }, nb::arg("status_base"), nb::arg("status_dyes"), nb::arg("status_weights"), nb::arg("view_base"), nb::arg("view_dyes"), nb::arg("view_weights"),
     nb::arg("xyz_scale"), nb::arg("axis_start"), nb::arg("axis_range"), nb::arg("axis_power"), nb::arg("nodes"), nb::arg("iterations"), nb::arg("reached_limit"));

  m.def("compose_print_table", [](Doubles paper_log, Doubles balance_log10, Doubles aim_log_h, Doubles contrast, double flash, Doubles surface_xyz,
                                  Doubles curve_density, Int64s curve_lengths, Doubles curve_start, double curve_step,
                                  Doubles axis_start, Doubles axis_range, double axis_power, Doubles paper_table, Bytes not_reached) {
    RequireShape(paper_log, "paper_log", {-1, 3});
    for (const Doubles* array : {&balance_log10, &aim_log_h, &contrast, &surface_xyz, &curve_start, &axis_start, &axis_range}) RequireShape(*array, "a value per layer", {3});
    RequireShape(curve_density, "curve_density", {3, -1});
    RequireShape(curve_lengths, "curve_lengths", {3});
    const int64_t stored = static_cast<int64_t>(curve_density.shape(1));
    for (int k = 0; k < 3; ++k) {
      if (curve_lengths.data()[k] < 2 || curve_lengths.data()[k] > stored) throw nb::value_error("curve_lengths: a length is outside the stored curve");
    }
    RequireShape(paper_table, "paper_table", {-1, -1, -1, 3});
    const int64_t n = static_cast<int64_t>(paper_table.shape(0));
    RequireShape(paper_table, "paper_table", {n, n, n, 3});
    RequireShape(not_reached, "not_reached", {n, n, n});
    const size_t count = paper_log.shape(0);
    auto out = NewArray<double>({count, size_t{3}});
    ft::ComposeCounts counts{};
    {
      nb::gil_scoped_release release;
      counts = ft::ComposePrintTable(paper_log.data(), static_cast<int64_t>(count), {balance_log10.data(), aim_log_h.data(), contrast.data(), flash, surface_xyz.data()},
                                     {stored, curve_density.data(), curve_lengths.data(), curve_start.data(), curve_step}, {n, axis_start.data(), axis_range.data(), axis_power},
                                     paper_table.data(), not_reached.data(), out.data());
    }
    return nb::make_tuple(out, counts.outside_curve, counts.print_not_reached);
  }, nb::arg("paper_log"), nb::arg("balance_log10"), nb::arg("aim_log_h"), nb::arg("contrast"), nb::arg("flash"), nb::arg("surface_xyz"),
     nb::arg("curve_density"), nb::arg("curve_lengths"), nb::arg("curve_start"), nb::arg("curve_step"), nb::arg("axis_start"), nb::arg("axis_range"), nb::arg("axis_power"), nb::arg("paper_table"), nb::arg("not_reached"));
}
