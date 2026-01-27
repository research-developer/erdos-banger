import Lake
open Lake DSL

package erdos where
  -- Package configuration
  leanOptions := #[
    ⟨`autoImplicit, false⟩,  -- Require explicit type annotations
    ⟨`pp.unicode.fun, true⟩,  -- Pretty print with Unicode
  ]

-- Pin mathlib to a specific version for reproducibility
-- Update this version along with lean-toolchain when upgrading
require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.27.0"

@[default_target]
lean_lib Erdos where
  -- Library configuration
  globs := #[.submodules `Erdos]
