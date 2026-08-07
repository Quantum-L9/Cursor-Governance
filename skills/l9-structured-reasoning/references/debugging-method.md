# Evidence-First Debugging

1. Reproduce the failure with expected versus actual behavior and environment.
2. Isolate the smallest failing layer or component.
3. Form one specific, testable hypothesis.
4. Identify evidence that would disconfirm it.
5. Run the cheapest discriminating probe.
6. Apply the minimal root-cause fix.
7. Re-run the original reproduction and add a regression test.
8. Stop when the root cause is proven and the regression guard passes.

Use binary search, layer isolation, or Git bisect only when the environment supports them and the expected information gain justifies the cost.

Never patch randomly, retry blindly, or treat symptom removal as root-cause proof.
