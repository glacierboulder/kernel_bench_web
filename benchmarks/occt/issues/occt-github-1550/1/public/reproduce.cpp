// Copyright (c) 2026 OPEN CASCADE SAS
//
// This file is part of Open CASCADE Technology software library.
//
// This library is free software; you can redistribute it and/or modify it under
// the terms of the GNU Lesser General Public License version 2.1 as published
// by the Free Software Foundation, with special exception defined in the file
// OCCT_LGPL_EXCEPTION.txt. Consult the file LICENSE_LGPL_21.txt included in OCCT
// distribution for complete text of the license and disclaimer of any warranty.
//
// Alternatively, this file may be used under the terms of Open CASCADE
// commercial license or contractual agreement.

#include <GeomAdaptor_Curve.hxx>
#include <GeomFill_Boundary.hxx>
#include <GeomFill_CoonsAlgPatch.hxx>
#include <GeomFill_SimpleBound.hxx>
#include <Geom_TrimmedCurve.hxx>
#include <GC_MakeSegment.hxx>
#include <Precision.hxx>
#include <gp_Pnt.hxx>
#include <gp_Vec.hxx>
#include <gp_XYZ.hxx>


#include <cmath>
#include <cstdio>
#include <iostream>
static int failures = 0;
struct Check {
  bool ok;
  explicit Check(bool pass, const char* expr, int line) : ok(pass) {
    if (!ok) { ++failures; std::cerr << line << " failed: " << expr << " "; }
  }
  ~Check() { if (!ok) std::cerr << '\n'; }
  template<class T> Check& operator<<(const T& value) {
    if (!ok) std::cerr << value;
    return *this;
  }
};
#define TEST(suite, name) static void name()
#define CHECK(expr) Check(bool(expr), #expr, __LINE__)
#define EXPECT_EQ(a,b) CHECK((a)==(b))
#define EXPECT_LE(a,b) CHECK((a)<=(b))
#define EXPECT_TRUE(a) CHECK(a)
#define EXPECT_NEAR(a,b,t) CHECK(std::abs((a)-(b))<=(t))
#define ASSERT_TRUE(a) if (!(a)) return (void)CHECK(false); else CHECK(true)
#define ASSERT_FALSE(a) ASSERT_TRUE(!(a))
#define ASSERT_EQ(a,b) ASSERT_TRUE((a)==(b))
#define ASSERT_DOUBLE_EQ(a,b) ASSERT_EQ(a,b)


#include <initializer_list>

namespace
{
//==================================================================================================

// Create a segment boundary with its native arc-length parameter range.
static occ::handle<GeomFill_SimpleBound> Bound(const gp_Pnt& theP1, const gp_Pnt& theP2)
{
  const occ::handle<Geom_TrimmedCurve> aSegment = GC_MakeSegment(theP1, theP2).Value();
  const occ::handle<GeomAdaptor_Curve> aCurve   = new GeomAdaptor_Curve(aSegment);
  return new GeomFill_SimpleBound(aCurve, Precision::Confusion(), Precision::Angular());
}
} // namespace

//==================================================================================================

// The four boundaries of a planar square, in the order the constructor expects: B1 and B3 run
// along U, B2 and B4 along V. Value(U, V) must sample B1 and B3 at U, as D1U and D1V do.
TEST(GeomFill_CoonsAlgPatchTest, ValueUsesUForTheUDirectionBoundaries)
{
  const gp_Pnt aP00(0., 0., 0.);
  const gp_Pnt aP10(10., 0., 0.);
  const gp_Pnt aP11(10., 10., 0.);
  const gp_Pnt aP01(0., 10., 0.);

  const occ::handle<GeomFill_Boundary> aB1 = Bound(aP00, aP10); // v = vMin, along U
  const occ::handle<GeomFill_Boundary> aB2 = Bound(aP10, aP11); // u = uMax, along V
  const occ::handle<GeomFill_Boundary> aB3 = Bound(aP01, aP11); // v = vMax, along U
  const occ::handle<GeomFill_Boundary> aB4 = Bound(aP00, aP01); // u = uMin, along V
  GeomFill_CoonsAlgPatch               aPatch(aB1, aB2, aB3, aB4);

  // The patch is parametrized on the boundaries' own ranges, U on B1's and V on B2's, which for
  // a segment is its arc length rather than [0, 1].
  double aUMin, aUMax, aVMin, aVMax;
  aB1->Bounds(aUMin, aUMax);
  aB2->Bounds(aVMin, aVMax);

  // On a planar square the patch is the plane itself, so the answer is known in closed form.
  const double aTol = Precision::Confusion();
  EXPECT_NEAR(aPatch.Value(aUMin, aVMin).Distance(aP00), 0., aTol);
  EXPECT_NEAR(aPatch.Value(aUMax, aVMin).Distance(aP10), 0., aTol);
  EXPECT_NEAR(aPatch.Value(aUMax, aVMax).Distance(aP11), 0., aTol);
  EXPECT_NEAR(aPatch.Value(aUMin, aVMax).Distance(aP01), 0., aTol);

  // Check distinct U and V values on the boundaries and inside the patch.
  const double aUMid = 0.5 * (aUMin + aUMax);
  const double aVMid = 0.5 * (aVMin + aVMax);
  EXPECT_NEAR(aPatch.Value(aUMax, aVMid).Distance(gp_Pnt(10., 5., 0.)), 0., aTol);
  EXPECT_NEAR(aPatch.Value(aUMin, aVMid).Distance(gp_Pnt(0., 5., 0.)), 0., aTol);
  EXPECT_NEAR(aPatch.Value(aUMid, aVMin).Distance(gp_Pnt(5., 0., 0.)), 0., aTol);
  EXPECT_NEAR(aPatch.Value(aUMid, aVMax).Distance(gp_Pnt(5., 10., 0.)), 0., aTol);
  EXPECT_NEAR(aPatch.Value(3., 7.).Distance(gp_Pnt(3., 7., 0.)), 0., aTol);
}

//==================================================================================================



//==================================================================================================





int main() { ValueUsesUForTheUDirectionBoundaries(); std::puts(failures ? "verdict=fail" : "verdict=pass"); return failures ? 1 : 0; }
