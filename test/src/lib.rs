#![cfg_attr(any(feature = "unstable", feature = "custom-unstable"), feature(test))]
#[cfg(any(feature = "unstable", feature = "custom-unstable"))]
extern crate test;

pub fn function() {
    println!("hi");
}

pub fn function2() {
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
