                         GITHUB REPOSITORY
                    ┌─────────────────────────┐
                    │ target.py               │
                    │ module_a.py             │
                    │ module_b.py             │
                    │ ...                     │
                    └───────────┬─────────────┘
                                │
                         GitHub Tool
                                │
                                ▼
                    ┌──────────────────────┐
                    │      AGENT 1         │
                    │   Code Analyzer      │
                    │                      │
                    │ Uses:                │
                    │ analyzer_skills.md   │◄──── Skills Tool
                    └──────────┬───────────┘
                               │
                         Analysis JSON
                      (internal artifact)
                               │
                               ▼
                    ┌──────────────────────┐
                    │      AGENT 2         │
                    │ Refactoring Architect│
                    │                      │
                    │ Uses:                │
                    │ blueprint_skills.md  │◄──── Skills Tool
                    └──────────┬───────────┘
                               │
                        Blueprint JSON
                      (internal artifact)
                               │
                               ▼
                    ┌──────────────────────┐
                    │      AGENT 3         │
                    │ Refactoring Generator│
                    │                      │
                    │ Uses:                │
                    │ generator_skills.md  │◄──── Skills Tool
                    └──────────┬───────────┘
                               │
                        Refactored .py
                               │
                               ▼
                    ┌──────────────────────┐
                    │      AGENT 4         │
                    │ Refactoring Validator│
                    │                      │
                    │ Uses:                │
                    │ validator_skills.md  │◄──── Skills Tool
                    │                      │
                    │ + Validation Tools   │
                    └──────────┬───────────┘
                               │
                         Validation result
                      (internal assessment)
                               │
                               ▼
                    ┌──────────────────────┐
                    │    FINAL OUTPUT      │
                    │                      │
                    │  Refactored .py      │
                    └──────────────────────┘