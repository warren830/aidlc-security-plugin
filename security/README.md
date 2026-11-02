# security

An AIDLC plugin scaffold. Replace the placeholders and example content with
your plugin's stages, scopes, agents, contributions, sensors, knowledge, and
runtime tools.

## Authoring flow

1. **Create:** `bun <tools-dir>/aidlc-plugin-create.ts security`
2. **Author:** edit `stages/`, `scopes/`, `agents/`, and the manifest.
3. **Validate:** `bun <tools-dir>/aidlc-plugin-validate.ts .`
4. **Build:** `bun <tools-dir>/aidlc-plugin-build.ts . claude`
5. **Test:** `bun <tools-dir>/aidlc-plugin-test.ts . --install <project-root> --harness claude`
6. **Publish:** build every supported harness projection, tag releases with
   SemVer, and publish the generated host plugin directories.

The build output defaults to `dist/<harness>/`. Publish those outputs from a
git repository with a `marketplace.json` so host-native plugin stores can
discover them. See the AIDLC plugin authoring guide for marketplace metadata
and host installation examples.

`hooks/compose.ts` is intentionally absent from this authored root. Plugin
build injects the current bundled compose hook into each host projection.
