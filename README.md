External repository for Bitcoin Core related maintenance tools.

github-merge
------------

A small script to automate merging pull-requests securely and sign them with GPG.

For example:

```bash
./github-merge.py 1234
```

(in any git repository) will help you merge pull request #1234 for the configured repository.

What it does:
* Fetch master and the pull request.
* Locally construct a merge commit.
* Show the diff that merge results in.
* Ask you to verify the resulting source tree (so you can do a make check or whatever).
* Ask you whether to GPG sign the merge commit.
* Ask you whether to push the result upstream.

This means that there are no potential race conditions (where a
pull request gets updated while you're reviewing it, but before you click
merge), and when using GPG signatures, that even a compromised GitHub
couldn't mess with the sources.

### Setup

Configuring the github-merge tool for the bitcoin repository is done in the following way:

    git config githubmerge.repository bitcoin/bitcoin
    git config githubmerge.testcmd "make -j4 check" (adapt to whatever you want to use for testing)
    git config --global user.signingkey mykeyid

If you want to use HTTPS instead of SSH for accessing GitHub, you need set the host additionally:

    git config githubmerge.host "https://github.com"  (default is "git@github.com", which implies SSH)

### Authentication (optional)

The API request limit for unauthenticated requests is quite low, but the
limit for authenticated requests is much higher. If you start running
into rate limiting errors it can be useful to set an authentication token
so that the script can authenticate requests.

- First, go to [Personal access tokens](https://github.com/settings/tokens).
- Click 'Generate new token'.
- Fill in an arbitrary token description. No further privileges are needed.
- Click the `Generate token` button at the bottom of the form.
- Copy the generated token (should be a hexadecimal string)

Then do:

    git config --global user.ghtoken "pasted token"

### Create and verify timestamps of merge commits

To create or verify timestamps on the merge commits, install the OpenTimestamps
client via `pip3 install opentimestamps-client`. Then, download the gpg wrapper
`ots-git-gpg-wrapper.sh` and set it as git's `gpg.program`. See
[the ots git integration documentation](https://github.com/opentimestamps/opentimestamps-client/blob/master/doc/git-integration.md#usage)
for further details.

update-translations
-------------------

Run this script from the root of a repository to update all translations from Transifex.
It will do the following automatically:

- Fetch all translations
- Post-process them into valid and committable format
- Add missing translations to the build system (TODO)

clang-format
------------

A script to format cpp source code according to the .clang-format file in the bitcoin repo.
This should only be applied to new files or files which are currently not actively developed on.
Also, git subtrees are not subject to formatting.

Note: The script is currently untested and unmaintained, but kept for archival reasons, in
case it is planned to be used some day.

build-for-compare
--------------------

Build for binary comparison.

See `build-for-compare.py --help` for more information.

Builds from current directory, which is assumed to be a git clone of the bitcoin repository.

**DO NOT RUN this with the nocopy=1 flag set on working tree if you have any local additions, it will nuke all
non-repository files, multiple times over. By leaving nocopy off (default) the git tree is copied to a temporary
directory and all operations are performed there.**

Example:
```bash
git clone https://github.com/bitcoin/bitcoin.git bitcoin-compare
cd bitcoin-compare
../bitcoin-maintainer-tools/build-for-compare.py 4731cab 2f71490
sha256sum /tmp/compare/bitcoind.*.stripped
git diff -W --word-diff /tmp/compare/4731cab /tmp/compare/2f71490
```

backport
--------

Script to backport pull requests in order of merge, to minimize number of conflicts.
Pull ids are listed in `to_backport.txt` or given on the command line.

Requires `pip3 install gitpython` or similar.

unittest-statistics
--------------------------

`unittest-statistics.py` can be used to print a table of the slowest 20 unit tests.

Usage:
```bash
unittest-statistics.py </path/to/test_bitcoin> [<subtest>]
```

For example:
```bash
unittest-statistics.py src/test/test_bitcoin wallet_tests
```

treehash512
--------------

This script will show the SHA512 tree has for a certain commit, or HEAD
by default.

Usage:

```bash
treehash512.py [<commithash>]
```

This should match the Tree-SHA512 commit metadata field added by
github-merge.

signoff
----------

This is an utility to manually add a treehash to the HEAD commit and then
gpg-sign it. This is useful when there is the need to manually add a commit.

Usage:

```bash
signoff.py
```
(no command line arguments)

When there is already a treehash on the HEAD commit, it is compared against
what is computed. If this matches, it continues. If the treehash mismatches an
error is thrown. If there is no treehash it adds the "Tree-SHA512:" header with
the computed hash to the commit message.

After making sure the treehash is correct it verifies whether the commit is
signed. If so it just displays the signature, if not, it is signed.

subtree updates
---------------

Bitcoin Core comes with several subtrees (c.f. https://github.com/bitcoin/bitcoin/tree/master/test/lint#git-subtree-checksh)
To update the subtree, make sure to fetch the remote of the subtree.
Then a simple call should pull in and squash the changes:

```sh
git subtree pull --prefix src/${prefix} ${remote_repo} ${ref} --squash
```

For setting up a subtree, refer to `git help subtree`.

check-dnsseeds
---------------

Sanity-check the DNS seeds used by Bitcoin Core.

Usage:

```bash
check-dnsseeds.py
```

Example output:

```bash
* Mainnet
OK   seed.bitcoin.sipa.be (40 results)
OK   dnsseed.bluematt.me (33 results)
FAIL dnsseed.bitcoin.dashjr.org
OK   seed.bitcoinstats.com (50 results)
OK   seed.bitcoin.jonasschnelli.ch (38 results)
OK   seed.btc.petertodd.org (23 results)
OK   seed.bitcoin.sprovoost.nl (35 results)
OK   dnsseed.emzy.de (41 results)

* Testnet
OK   testnet-seed.bitcoin.jonasschnelli.ch (36 results)
OK   seed.tbtc.petertodd.org (38 results)
OK   testnet-seed.bluematt.me (5 results)
```

delete non-reduced fuzz inputs
------------------------------

Refer to the documentation inside the script.

fastcopy-chaindata
-------------------

Fast local copy of Bitcoin Core blockchain state.

```bash
fastcopy-chaindata.py ~/.bitcoin /path/to/temp/datadir
```

This utility hardlinks all but the last block data file (rev and blk),
and hardlinks all .ldb files to the destination. The last data files as well
as the other leveldb data files (such as the log) are copied.

This relies on the fact that block files (except the last) and ldb files
are read-only once they are written.

Warning: Hardlinking only works within a filesystem, and may not work for all
filesystems.

transifex-migrate-resource
--------------------------

Copy a transifex resource to another.

Run the script providing the slug of the project and the slug of the old and new resource.
The new resource should already have been created, but be otherwise empty. It should
be based on the exact same source translation.
 
Example:
Old resource slug: 'old'
New resource slug: 'new'
 
python transifex-migrate-resource.py project old new
 
After running the command you will be asked for your Transifex username and password.

list-pulls
----------

Script to parse git commit list, extract github issues to create a changelog in
text and json format.

Run this in the root directory of the repository.

This requires an up-to-date checkout of https://github.com/zw/bitcoin-gh-meta.git
in the parent directory, or environment variable `GHMETA`.

It takes a range of commits and a .json file of PRs to exclude, for
example if these are already backported in a minor release. This can be the pulls.json
generated from a previous release.

Example usage:

    ../maintainer-tools/list-pulls.py v0.18.0 0.19 relnot/pulls-exclude.json > relnot/pulls.md

The output of this script is a first draft based on rough heuristics, and
likely needs to be extensively manually edited before ending up in the release
notes.

make-tag
--------

Make a new release tag, performing a few checks.

Usage: `make-tag.py <tag>`.

gitian-verify
-------------

A script to verify gitian deterministic build signatures for a release in one
glance. It will print a matrix of signer versus build package, and a list of
missing keys.

To be able to read gitian's YAML files and verify PGP signatures, it needs the
`pyyaml` and `gpg` modules. This can be installed from pip, for example:

```bash
pip3 install --user pyyaml gpg
```
(or install the distribution package, in Debian/Ubuntu this is `python3-yaml` and `python3-gpg`)

Example usage: `./gitian-verify.py -r 0.21.0rc5 -d ../gitian.sigs -k ../bitcoin/contrib/gitian-keys/keys.txt`

Where

- `-r 0.21.0rc5` specifies the release to verify signatures for.
- `-d ../gitian.sigs` specifies the directory where the repository with signatures, [gitian.sigs](https://github.com/bitcoin-core/gitian.sigs/) is checked out.
- `../bitcoin/contrib/gitian-keys/keys.txt` is the path to `keys.txt` file inside the main repository that specifies the valid keys and what signers they belong to.

Example output:
```
Signer            linux      osx-unsigned  win-unsigned   osx-signed    win-signed
justinmoon        No Key        No Key        No Key        No Key        No Key
laanwj              OK            OK            OK            OK            OK
luke-jr             OK            OK            OK            OK            OK
marco               -             OK            OK            OK            OK

Missing keys
norisg         3A51FF4D536C5B19BE8800A0F2FC9F9465A2995A  from GPG, from keys.txt
...
```

See `--help` for the full list of options and their descriptions.

The following statuses can be shown:

- `Ok` Full match.
- `No key` Signer name/key combination not in keys.txt, or key not known to GPG (which one of these it is, or both, will be listed under "Missing keys").
- `Expired` Known key but it has expired.
- `Bad` Known key but invalid PGP signature.
- `Mismatch` Correct PGP signature but mismatching binaries.

ghwatch
-------

This is a script to watch your github notifications in the terminal. It will show a table that is refreshed every 10 minutes (configurable). It can be exited by pressing <kbd>ESC</kbd> or <kbd>Ctrl-C</kbd>.

### Dependencies

The `github` python module is a required dependency for github API access. This can be installed for your user using `pip3 install --user PyGithub`, or globally using your distribution's package manager e.g. `apt-get install python3-github`.

### Configuration

To generate a default configuration file in `~/.config/ghwatch/ghwatch.conf` do

```
./ghwatch.py --default-config
```

Then, edit the configuration file. Only thing that is necessary to change is `ghtoken`. You will need to create a github [authentication token](https://github.com/settings/tokens) then insert it here:

```
    "ghtoken": "<token from github>",
```

Depending on your browser preference you might want to change `browser`, this is the command that will be invoked when clicking on an issue number. It defaults to `null` which indicates to use the system web browser.

If you want to see PR status (and other issue details like labels), point `meta` for the `bitcoin/bitcoin` repository to an up-to-date checkout of [bitcoin-gh-meta](https://github.com/zw/bitcoin-gh-meta).
```
    "meta": {
        "bitcoin/bitcoin": "/path/to/bitcoin-gh-meta"
    },
```

To keep this repository up to date you can set the interval in seconds in 'auto_update', default is 0 (i.e. no automatic update). Be aware that [bitcoin-gh-meta](https://github.com/zw/bitcoin-gh-meta) is being refreshed every two hours (7200 seconds).

Sorting the notifications by {reason, time} can be enabled with the 'sort_notifications' boolean field (default=false).

By editing the `label_prio` structure it is possible to affect what labels will be shown. The first label encountered in this list for an issue in the associated repository will be shown as the label in the table.

### Command-line options

Some other settings can be set through command line options. See `./ghwatch.py --help` for the list of command line options and their descriptions.

### Display

Most of the columns are self-explanatory, except for:

- `r` this [notification reason](https://docs.github.com/en/rest/reference/activity#notification-reasons) from the GH API as a two-letter code. This can be:
  - `as` assign
  - `au` author
  - `co` comment
  - `in` invitation
  - `ma` manual
  - `me` mention
  - `rr` review requested
  - `sa` security alert
  - `sc` state change
  - `su` subscribed
  - `tm` team mention
- `k` the kind of notification as a letter. This can be:
  - `P` pull request
  - `I` issue
  - `C` commit

### Controls

Left-click on a PR number to show details in a web browser.

The program can be exited by pressing <kbd>ESC</kbd> or <kbd>Ctrl-C</kbd>.
