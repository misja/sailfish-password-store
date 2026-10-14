# Maintaining the upstream delta

Source adaptations live in upstream forks. This repository owns integration and
packaging; its patch files are packaging snapshots, not a second editing location.

With all six repositories checked out as siblings, run:

~~~sh
python3 ../sailfish-workspace/tools/packaging-patches.py
~~~

This applies the snapshots to each pinned upstream Git tree and compares the
complete result, including paths, modes and added files, with the fork tree.
It does not fetch, build, install or access user data.

For an approved source change, commit it in the responsible fork, update its
source locks and the workspace source map, then regenerate snapshots:

~~~sh
python3 ../sailfish-workspace/tools/packaging-patches.py --export
python3 ../sailfish-workspace/tools/packaging-patches.py
~~~

The export currently maps one ordered fork commit to each packaging patch.
A changed commit count requires updating tools/packaging-patches.json and the
affected recipe together. Review the regenerated patch diff and run the affected
behavior/package checks before merging. Full-tree equality alone does not
establish runtime or release acceptance.

The recipes continue to authenticate upstream archives and apply these patches.
Do not replace them with already patched fork archives and apply the patches
again. Upstream updates and upstream submissions are separate reviewed work.
