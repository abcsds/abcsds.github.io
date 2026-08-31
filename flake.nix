{
  description = "abcsds.github.io — personal academic site (Jekyll / academicpages fork)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Everything the CV generator needs. The Jekyll build itself is NOT
        # packaged here: the site depends on jekyll-polyglot and a pinned
        # Gemfile.lock, so it is built by bundler (locally via the Dockerfile /
        # devcontainer, and in CI by .github/workflows/pages-deploy.yml).
        python = pkgs.python3.withPackages (ps: [ ps.pyyaml ]);

        # _data/cv.json is a *derived* artifact. Single source of truth:
        #   _config.yml `author:`  -> basics
        #   _pages/cv.md           -> education, work, skills, languages,
        #                             portfolio, interests
        #   _publications, _talks, _teaching -> the collections
        cv-json = pkgs.writeShellApplication {
          name = "cv-json";
          runtimeInputs = [ python ];
          text = ''
            root="''${1:-$PWD}"
            if [ ! -f "$root/_pages/cv.md" ]; then
              echo "error: $root does not look like the site repo (_pages/cv.md missing)" >&2
              exit 1
            fi
            python3 "$root/scripts/cv_markdown_to_json.py" \
              --input  "$root/_pages/cv.md" \
              --output "$root/_data/cv.json" \
              --config "$root/_config.yml"
          '';
        };
      in
      {
        packages.cv-json = cv-json;
        packages.default = cv-json;

        # nix run .#cv-json     — regenerate _data/cv.json in the current repo
        apps.cv-json = {
          type = "app";
          program = "${cv-json}/bin/cv-json";
        };
        apps.default = self.apps.${system}.cv-json;

        # nix develop           — python + pyyaml for the generator
        devShells.default = pkgs.mkShell {
          packages = [ python cv-json pkgs.jq ];
          shellHook = ''
            echo "abcsds.github.io dev shell"
            echo "  cv-json          regenerate _data/cv.json from _pages/cv.md + collections"
            echo "  nix flake check  verify _data/cv.json is in sync with its sources"
          '';
        };

        # nix flake check       — fails if the committed cv.json is stale.
        # CI regenerates it on deploy anyway, so this is a local early warning.
        checks.cv-json-sync = pkgs.runCommand "cv-json-sync"
          {
            nativeBuildInputs = [ python pkgs.diffutils ];
          } ''
          cp -r ${self} src
          chmod -R u+w src
          python3 src/scripts/cv_markdown_to_json.py \
            --input  src/_pages/cv.md \
            --output "$TMPDIR/cv.json" \
            --config src/_config.yml
          if ! diff -u src/_data/cv.json "$TMPDIR/cv.json"; then
            echo ""
            echo "_data/cv.json is out of date. Run:  nix run .#cv-json" >&2
            exit 1
          fi
          touch $out
        '';
      });
}
