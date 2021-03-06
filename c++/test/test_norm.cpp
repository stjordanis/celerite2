#define CATCH_CONFIG_MAIN

#include "catch.hpp"
#include "helpers.hpp"
#include <Eigen/Dense>
#include <celerite2/celerite2.h>

using namespace celerite2::test;
using namespace celerite2::core;

TEMPLATE_LIST_TEST_CASE("check the results of norm", "[norm]", TestKernels) {
  SETUP_TEST(50);

  Matrix K, S, F, Z, result;
  to_dense(a, U, V, P, K);

  // Do the solve using celerite
  int flag = factor(a, U, V, P, a, V, S);
  REQUIRE(flag == 0);

  // Brute force the solve
  Eigen::LDLT<Matrix> LDLT(K);
  Matrix expect = Y.transpose() * LDLT.solve(Y);

  SECTION("general") {
    norm(U, P, a, V, Y, result, Z, F);
    double resid = (expect - result).array().abs().maxCoeff();
    REQUIRE(resid < 1e-12);
  }

  SECTION("no grad") {
    norm(U, P, a, V, Y, result, Z);
    double resid = (expect - result).array().abs().maxCoeff();
    REQUIRE(resid < 1e-12);
  }

  SECTION("inplace") {
    Z = Y;
    norm(U, P, a, V, Z, result, Z, F);
    double resid = (expect - result).array().abs().maxCoeff();
    REQUIRE(resid < 1e-12);
  }
}
