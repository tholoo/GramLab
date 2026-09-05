# Completion requirements

At each handoff:

1. Reconcile every changed file with the task and preserve unrelated work.
2. Demonstrate the behavioral regression/contract at its public boundary. Record red/green
   evidence where implementation changed; validate config/docs directly for scaffold-only work.
3. Run the applicable tooling from [CONTRIBUTING.md](../../CONTRIBUTING.md). Report unavailable
   Android, conformance or performance coverage explicitly. No-tests is not a passed suite.
4. Review documentation impact: terminology, architecture, configuration, safety, compatibility,
   operations, examples, licensing and contributor workflow. Update affected records together.
5. Update the local ticket and compatibility evidence with what was actually verified. Include
   reproducible commands, profile/run IDs and relevant artifacts without credentials.
6. Report Git state, remaining work and next action. Publish remotely only with explicit approval;
   preserve local work even when no remote exists. Remove only dedicated, no-longer-needed runtime
   resources after evidence is safe.

Scaffold completion means coherent directories, config, documents and handoff—not a working bot
simulator. Runtime completion additionally needs real behavioral evidence and safety enforcement.
