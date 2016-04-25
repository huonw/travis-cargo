#![cfg_attr(any(feature = "unstable", feature = "custom-unstable"), feature(test))]
#[cfg(any(feature = "unstable", feature = "custom-unstable"))]
extern crate test;

extern crate dylib;

pub fn function() {
    // call something so the linker doesn't kill it
    dylib::foo();

    println!("hi");
}

pub fn function2() {
    // call something so the linker doesn't kill it
    dylib::foo();

    println!("hi");
}


#[test]
fn incrate() {
    function2()
}

#[cfg(not(feature = "remove-failing"))]
#[test]
fn panics() {
    panic!()
}

#[cfg(feature = "unstable")]
#[test]
fn default_unstable_test() {}

#[cfg(feature = "custom-unstable")]
#[test]
fn custom_unstable_test() {}

#[cfg(any(feature = "unstable", feature = "custom-unstable"))]
#[bench]
fn unstable_benchmark(b: &mut test::Bencher) {
    b.iter(|| 0)
}
