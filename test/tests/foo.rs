#![cfg_attr(feature = "unstable", feature(non_ascii_idents))]
extern crate travis_cargo_test;

extern crate dylib;

#[test]
fn foo() {
    travis_cargo_test::function();
}

#[cfg(feature = "unstable")]
#[test]
fn bár() {}
