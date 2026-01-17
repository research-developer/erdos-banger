-- Erdos/Basic.lean
-- Common definitions and imports for Erdős problem formalizations

import Mathlib.Data.Nat.Prime
import Mathlib.Data.Finset.Basic
import Mathlib.Algebra.BigOperators.Basic
import Mathlib.Combinatorics.SimpleGraph.Basic

-- Mark this as an Erdős problem (for metadata)
structure ErdosProblem where
  id : Nat
  title : String
  status : String  -- "open", "proved", "disproved"
  deriving Repr

-- Common tactics and lemmas can be added here
