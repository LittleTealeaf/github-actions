//! Sample crate documentation for testing actions.

/// Adds two numbers together.
///
/// # Examples
/// ```
/// use sample_crate::add;
/// assert_eq!(add(1, 2), 3);
/// ```
pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}
