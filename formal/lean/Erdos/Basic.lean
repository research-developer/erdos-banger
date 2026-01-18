-- Erdos/Basic.lean
-- Common definitions and imports for Erdős problem formalizations

import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Algebra.BigOperators.Group.Finset
import Mathlib.Combinatorics.SimpleGraph.Basic

-- Mark this as an Erdős problem (for metadata)
structure ErdosProblem where
  id : Nat
  title : String
  status : String  -- "open", "proved", "disproved"
  deriving Repr

-- Common tactics and lemmas can be added here
