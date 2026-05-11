use wasm_bindgen::prelude::*;

/// Cuenta palabras en un texto (Rust → WASM → JS en el Dashboard)
#[wasm_bindgen]
pub fn count_words(text: &str) -> usize {
    text.split_whitespace().count()
}

/// Cuenta caracteres (útil para métricas del wiki)
#[wasm_bindgen]
pub fn count_chars(text: &str) -> usize {
    text.chars().count()
}

/// Cuenta frases
#[wasm_bindgen]
pub fn count_sentences(text: &str) -> usize {
    text.split(|c| c == '.' || c == '!' || c == '?')
        .filter(|s| !s.trim().is_empty())
        .count()
}

/// Calcula coherence score simulado (placeholder para Neural Attention Engine)
#[wasm_bindgen]
pub fn coherence_score(pages: usize, contradictions: usize, orphans: usize) -> f64 {
    if pages == 0 { return 0.0; }
    let base = 1.0;
    let penalty = (contradictions as f64 * 0.05 + orphans as f64 * 0.02) / pages as f64;
    (base - penalty).max(0.0).min(1.0)
}

/// Hash rápido para witness tokens (SHA-256 simulado en WASM)
#[wasm_bindgen]
pub fn quick_hash(input: &str) -> String {
    // En producción usaría sha2 crate, aquí un hash simple
    let mut hash: u64 = 5381;
    for byte in input.bytes() {
        hash = ((hash << 5).wrapping_add(hash)).wrapping_add(byte as u64);
    }
    format!("{:016x}", hash)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_words() {
        assert_eq!(count_words("Hello world from Nova"), 4);
    }

    #[test]
    fn test_coherence() {
        let score = coherence_score(47, 0, 3);
        assert!(score > 0.9);
        assert!(score <= 1.0);
    }
}
