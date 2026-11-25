#include <GC_MakeSegment.hxx>
#include <GeomAdaptor_Curve.hxx>
#include <GeomFill_CoonsAlgPatch.hxx>
#include <GeomFill_SimpleBound.hxx>
#include <Geom_TrimmedCurve.hxx>
#include <Standard_Failure.hxx>
#include <gp_Pnt.hxx>
#include <gp_Vec.hxx>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace
{
constexpr double Tol = 1e-7;
constexpr std::array<double, 5> Stations{0., .125, .5, .875, 1.};
using Bound = occ::handle<GeomFill_SimpleBound>;

enum class Control { Native, Swap, ReverseU, ReverseV };

void Require(bool condition, const char* message)
{
  if (!condition) throw std::runtime_error(message);
}

Bound Segment(const gp_Pnt& start, const gp_Pnt& end, bool unit)
{
  const occ::handle<Geom_TrimmedCurve> segment = GC_MakeSegment(start, end).Value();
  const occ::handle<GeomAdaptor_Curve> curve = new GeomAdaptor_Curve(segment);
  const Bound bound = new GeomFill_SimpleBound(curve, Tol, 1e-12);
  const double last = unit ? 1. : start.Distance(end);
  if (unit) bound->Reparametrize(0., 1., false, false, 1., 1., false);
  double firstParam, lastParam;
  bound->Bounds(firstParam, lastParam);
  Require(std::abs(firstParam) <= Tol && std::abs(lastParam - last) <= Tol, "unexpected boundary parameter range");
  Require(bound->Value(firstParam).Distance(start) <= Tol && bound->Value(lastParam).Distance(end) <= Tol,
          "boundary endpoints or orientation differ from the reference");
  return bound;
}

struct Fixture
{
  const char* name;
  std::array<gp_Pnt, 4> corners;
  bool unit;
  double uSpan, vSpan;

  std::array<gp_Vec, 2> expected(double u, double v) const
  {
    // The native-parameter tilted rectangle and the normalized straight-sided
    // bilinear surface have closed-form tangents, independent of patch.Value().
    if (!unit) return {gp_Vec(.6, 0, .8), gp_Vec(0, 1, 0)};
    return {gp_Vec(10, 0, 2 - 3 * v), gp_Vec(0, 10, 1 - 3 * u)};
  }
};

struct Totals
{
  int goodU = 0, goodV = 0;
  double maxU = 0., maxV = 0.;
};

constexpr std::array<Control, 4> Controls{Control::Native, Control::Swap, Control::ReverseU, Control::ReverseV};
constexpr std::array<const char*, 4> Names{"native", "swap", "reverse-u", "reverse-v"};

void Write(std::ostream& stream, const gp_Vec& vec)
{
  stream << ',' << vec.X() << ',' << vec.Y() << ',' << vec.Z();
}

bool Inspect(const Fixture& fixture, std::ostream& trace)
{
  const auto& p = fixture.corners;
  GeomFill_CoonsAlgPatch patch(Segment(p[0],p[1],fixture.unit), Segment(p[1],p[2],fixture.unit),
                              Segment(p[3],p[2],fixture.unit), Segment(p[0],p[3],fixture.unit));
  std::array<Totals, Controls.size()> totals{};
  for (const double s : Stations)
  {
    for (const double t : Stations)
    {
      const double u = fixture.uSpan * s;
      const double v = fixture.vSpan * t;
      const auto expected = fixture.expected(u, v);
      const gp_Vec du = patch.D1U(u, v);
      const gp_Vec dv = patch.D1V(u, v);
      for (std::size_t index = 0; index < Controls.size(); ++index)
      {
        gp_Vec actualU = du;
        gp_Vec actualV = dv;
        switch (Controls[index])
        {
          case Control::Native: break;
          case Control::Swap: std::swap(actualU, actualV); break;
          case Control::ReverseU: actualU.Reverse(); break;
          case Control::ReverseV: actualV.Reverse(); break;
        }
        const double errorU = (actualU - expected[0]).Magnitude();
        const double errorV = (actualV - expected[1]).Magnitude();
        Require(std::isfinite(errorU) && std::isfinite(errorV), "non-finite tangent");
        auto& total = totals[index];
        total.goodU += errorU <= Tol;
        total.goodV += errorV <= Tol;
        total.maxU = std::max(total.maxU, errorU);
        total.maxV = std::max(total.maxV, errorV);
        trace << fixture.name << ',' << Names[index] << ',' << u << ',' << v;
        Write(trace, actualU);
        Write(trace, actualV);
        trace << '\n';
      }
    }
  }
  constexpr int all = Stations.size() * Stations.size();
  const std::array<std::array<int, 2>, Controls.size()> expectedPass{{
      {all, all}, {0, 0}, {0, all}, {all, 0},
  }};
  bool passed = true;
  for (std::size_t index = 0; index < Controls.size(); ++index)
  {
    const auto& total = totals[index];
    const bool pass = total.goodU == all && total.goodV == all;
    std::cout << "CONTROL " << fixture.name << ' ' << Names[index]
              << " good_u=" << total.goodU << " good_v=" << total.goodV
              << " max_u=" << total.maxU << " max_v=" << total.maxV
              << " verdict=" << (pass ? "PASS" : "FAIL") << '\n';
    passed &= total.goodU == expectedPass[index][0] && total.goodV == expectedPass[index][1];
  }
  return passed;
}
}

int main()
{
  try
  {
    const std::filesystem::path path("/workspace/gh1550-tangents.csv");
    Require(!std::filesystem::exists(path), "trace path must be new");
    std::ofstream trace(path);
    trace.exceptions(std::ios::badbit | std::ios::failbit);
    trace << std::setprecision(17) << "fixture,control,u,v,dux,duy,duz,dvx,dvy,dvz\n";
    std::cout << std::setprecision(17);
    const Fixture rectangle{"rectangle", {gp_Pnt(-3,2,5), gp_Pnt(3,2,13), gp_Pnt(3,8,13), gp_Pnt(-3,8,5)},
                            false, 10., 6.};
    const Fixture bilinear{"bilinear", {gp_Pnt(0,0,0), gp_Pnt(10,0,2), gp_Pnt(10,10,0), gp_Pnt(0,10,1)},
                           true, 1., 1.};
    const bool rectPass = Inspect(rectangle, trace);
    const bool bilinearPass = Inspect(bilinear, trace);
    trace.close();
    if (!rectPass || !bilinearPass) return 1;
    std::cout << "TEST_DONE\n";
    return 0;
  }
  catch (const Standard_Failure& error) { std::cerr << error.what() << '\n'; }
  catch (const std::exception& error) { std::cerr << error.what() << '\n'; }
  return 2;
}
