#!/usr/bin/env python3
# Written by W.J. van der Laan, provided under MIT license.
#
# Usage: ../do_build.py <hash> [<hash> ...]
# Will produce a ../bitcoind.$1.stripped for binary comparison
import os,subprocess,sys,argparse,logging,shutil,re,hashlib,shlex
from collections import defaultdict

logger = logging.getLogger('do_build')
# Use this command to compare resulting directories
# git diff -W --word-diff /tmp/compare/4b5b263 /tmp/compare/d1bc5bf

# WARNING WARNING WARNING
#   DO NOT RUN this on working tree if you have any local additions, it will nuke all non-repository files, multiple times over.
#   Ideally this would clone a git tree first to a temporary directory. Suffice to say, it doesn't.
# WARNING WARNING WARNING

CONFIGURE_EXTRA=[
'EVENT_CFLAGS=-I/opt/libevent/include',
'EVENT_LIBS=-L/opt/libevent/lib -levent',
'EVENT_PTHREADS_CFLAGS=-I/opt/libevent/include',
'EVENT_PTHREADS_LIBS=-L/opt/libevent/lib -levent_pthreads'
]
DEFAULT_PARALLELISM=4
DEFAULT_ASSERTIONS=0
DEFAULT_PATCH='stripbuildinfo.patch'

# No debugging information (not used by analysis at the moment, saves on I/O)
OPTFLAGS=["-O0","-g0"]
# Some options from -O to reduce code size
# can't use -O or -Os as it does some weird cross-contamination between unchanged functions in compilation unit
# Selectively enable opts that don't interfere or cause excessive sensitivity to changes
#
OPTFLAGS+=["-fcombine-stack-adjustments","-fcompare-elim","-fcprop-registers","-fdefer-pop","-fforward-propagate","-fif-conversion","-fif-conversion2",
        "-finline-functions-called-once","-fshrink-wrap","-fsplit-wide-types","-ftree-bit-ccp","-ftree-ccp","-ftree-ch","-ftree-copy-prop","-ftree-copyrename",
        "-ftree-dce","-ftree-dominator-opts","-ftree-dse","-ftree-fre","-ftree-sink","-ftree-slsr","-ftree-sra","-ftree-ter"
]
#
# -ffunctions-sections/-fdata-sections put every element in its own section. This is essential.
OPTFLAGS+=['-ffunction-sections', '-fdata-sections']
# Fix the random seed
OPTFLAGS+=['-frandom-seed=notsorandom']
# OFF: -fmerge-constants don't attempt to merge constants: this causes global interaction between sections/functions
# this was reenabled because it doesn't matter, the numbered section names are annoying merged or unmerged
OPTFLAGS+=['-fmerge-all-constants']
# -fipa-sra semi-randomly renames functions (or creates variants of functions with different names(
OPTFLAGS+=['-fno-ipa-sra']
# -freorder-functions moves functions to .unlikely .hot sections
OPTFLAGS+=['-fno-reorder-functions']
# no interprocedural optimizations
# -fno-ipa-profile -fno-ipa-pure-const -fno-ipa-reference -fno-guess-branch-probability -fno-ipa-cp

CPPFLAGS=[]
# Prevent __LINE__ from messing with things
#CPPFLAGS+=["-D__LINE__=0","-D__DATE__=\"\""] #-D__COUNTER__=0"
# XXX unfortunately this approach does not work thanks to boost.

# objcopy: strip all symbols, debug info, and the hash header section
OBJCOPY_ARGS=['-R.note.gnu.build-id','-g','-S']
OBJDUMP_ARGS=['-C','--no-show-raw-insn','-d','-r']

# These can be overridden from the environment
GIT=os.getenv('GIT', 'git')
MAKE=os.getenv('MAKE', 'make')
OBJCOPY=os.getenv('OBJCOPY', 'objcopy')
OBJDUMP=os.getenv('OBJDUMP', 'objdump')
OBJEXT=os.getenv('OBJEXT', '.o') # object file extension

TGTDIR='/tmp/compare'
PYDIR=os.path.dirname(os.path.abspath(__file__))
PATCHDIR=os.path.join(PYDIR,'patches')

def init_logging():
    LOG_PREFMT = {
        (logging.DEBUG, '\x1b[38;5;239m[%(name)-8s]\x1b[0m %(message)s\x1b[0m'),
        (logging.INFO,  '\x1b[38;5;19m>\x1b[38;5;18m>\x1b[38;5;17m> \x1b[38;5;239m[%(name)-8s]\x1b[0m %(message)s\x1b[0m'),
        (logging.WARNING, '\x1b[38;5;228m>\x1b[38;5;227m>\x1b[38;5;226m> \x1b[38;5;239m[%(name)-8s]\x1b[38;5;226m %(message)s\x1b[0m'),
        (logging.ERROR, '\x1b[38;5;208m>\x1b[38;5;202m>\x1b[38;5;196m> \x1b[38;5;239m[%(name)-8s]\x1b[38;5;196m %(message)s\x1b[0m'),
        (logging.CRITICAL, '\x1b[48;5;196;38;5;16m>>> [%(name)-8s] %(message)s\x1b[0m'),
    }

    class MyStreamHandler(logging.StreamHandler):
        def __init__(self, stream, formatters):
            logging.StreamHandler.__init__(self, stream)
            self.formatters = formatters
        def format(self, record):
            return self.formatters[record.levelno].format(record)

    formatters = {}
    for (level, fmtstr) in LOG_PREFMT:
        formatters[level] = logging.Formatter(fmtstr)
    handler = MyStreamHandler(sys.stdout, formatters)
    logging.basicConfig(level=logging.DEBUG, handlers=[handler])

def shell_split(s):
    return shlex.split(s)
def shell_join(s):
    return ' '.join(shlex.quote(x) for x in s)

def check_call(args):
    '''Wrapper for subprocess.check_call that logs what command failed'''
    try:
        subprocess.check_call(args)
    except Exception:
        logger.error('Command failed: %s' % shell_join(args))
        raise

def iterate_objs(srcdir):
    '''Iterate over all object files in srcdir'''
    for (root, dirs, files) in os.walk(srcdir):
        if not root.startswith(srcdir):
            raise ValueError
        root = root[len(srcdir)+1:]
        for filename in files:
            if filename.endswith(OBJEXT):
                yield os.path.join(root, filename)

def copy_o_files(srcdir,tgtdir):
    '''Copy all object files from srcdir to dstdir, keeping the same directory hierarchy'''
    for objname in iterate_objs(srcdir):
        outname = os.path.join(tgtdir, objname)
        os.makedirs(os.path.dirname(outname), exist_ok=True)
        shutil.copy(os.path.join(srcdir, objname), outname)

def objdump_all(srcdir,tgtdir):
    '''
    Object analysis pass using objdump.
    '''
    for objname in iterate_objs(srcdir):
        objname = os.path.join(srcdir, objname)
        p = subprocess.Popen([OBJDUMP] + OBJDUMP_ARGS + [objname], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out,err) = p.communicate()
        if p.returncode != 0:
            raise Exception('objdump failed')
        (out,err) = (out.decode(),err.decode())

        # postprocess- break into sections separated by 'Disassembly of section...'
        sections = defaultdict(list)
        funcname = ''
        for line in out.split('\n'):
            match = re.match('^Disassembly of section (.*):$', line)
            if match:
                funcname = match.group(1)
            if not '.rodata' in line:  # filter out 'ebc: R_X86_64_32        .rodata+0x1944'
                sections[funcname].append(line)

        '''
        lines = []
        for section in sorted(sections.keys()): # '' header section automatically comes first
            #lines.extend(sections[section])
            lines.append(sections[section][0])
        out = '\n'.join(lines)

        outname = os.path.join(tgtdir, objname[:-len(OBJEXT)] + '.dis')
        make_parent_dirs(outname)
        with open(outname, 'w') as f:
            f.write(out)
        '''
        for section in sections.keys():
            if not section:
                continue
            name = hashlib.sha1(section.encode()).hexdigest()
            outname = os.path.join(tgtdir, name + '.dis')
            os.makedirs(os.path.dirname(outname), exist_ok=True)
            with open(outname, 'w') as f:
                f.write('\n'.join(sections[section]))

    # some TODO s, learning about the objdump output:
    # - demangle section names
    # - remove/make relative addresses
    # - sort/combine sections
    # - remove duplicate sections? (sounds like linker's work - can we do a partial link that preserves sections, such as for inlines?)
    # - resolve callq's relocations - these are ugly right now - integrate reloc result into instruction by substituting argument
    #    - [-  17: R_X86_64_32S        vtable for boost::exception_detail::bad_exception_+0x30-]
    #    (at the very least delete callq's arguments)
    # - for data (mov etc): fill in data? pointers change arbitrarily especially in combined string tables (.rodata.str1...)
    #       and these entries don't have names/symbols
    # - or could use a different disassembler completely, such as capstone. Parsing objdump output is a hack.

def parse_arguments():
    parser = argparse.ArgumentParser(description='Build to compare binaries. Execute this from a repository directory.')
    parser.add_argument('commitids', metavar='COMMITID', nargs='+')
    parser.add_argument('--executables', default='src/bitcoind', help='Comma-separated list of executables to build, default is "src/bitcoind"')
    parser.add_argument('--tgtdir', default=TGTDIR, help='Target directory, default is "'+TGTDIR+'"')
    parser.add_argument('--parallelism', '-j', default=DEFAULT_PARALLELISM, type=int, help='Make parallelism, default is %s' % (DEFAULT_PARALLELISM))
    parser.add_argument('--assertions', default=0, type=int, help='Build with assertions, default is %s' % (DEFAULT_ASSERTIONS))
    parser.add_argument('--opt', default=None, type=str, help='Override C/C++ optimization flags. Prepend + to avoid collisions with arguments, e.g. "+-O2 -g"')
    parser.add_argument('--patches', '-P', default=None, type=str, help='Comma separated list of stripbuildinfo patches to apply, one per hash (in order).')
    args = parser.parse_args()
    args.patches = dict(zip(args.commitids, [v.strip() for v in args.patches.split(',')])) if args.patches is not None else {}
    args.executables = args.executables.split(',')
    if args.opt is not None:
        if not args.opt.startswith('+'):
            print('"opt" argument must start with +', file=sys.stderr)
            exit(1)
        args.opt = shell_split(args.opt[1:])
    else:
        args.opt = OPTFLAGS
    return args

def main():
    args = parse_arguments()
    init_logging()
    try:
        try:
            os.makedirs(args.tgtdir)
        except FileExistsError:
            logger.warning("%s already exists, remove it if you don't want to continue a current comparison session" % args.tgtdir)

        for commit in args.commitids:
            try:
                int(commit,16)
            except ValueError:
                logger.error('%s is not a hexadecimal commit id. It\'s the only thing we know.' % commit)
                exit(1)

        # Determine (g)make arguments
        make_args = []
        if args.parallelism is not None:
            make_args += ['-j%i' % args.parallelism]
        # Disable assertions if requested
        cppflags = CPPFLAGS
        if not args.assertions:
            cppflags+=['-DNDEBUG']

        for commit in args.commitids:
            logger.info("Building %s..." % commit)
            stripbuildinfopatch = args.patches[commit] if commit in args.patches else DEFAULT_PATCH
            commitdir = os.path.join(args.tgtdir, commit)
            commitdir_obj = os.path.join(args.tgtdir, commit+'.o')

            try:
                os.makedirs(commitdir)
            except FileExistsError:
                logger.error("%s already exists, remove it to continue" % commitdir)
                exit(1)
            check_call([GIT,'reset','--hard'])
            check_call([GIT,'clean','-f','-x','-d'])
            check_call([GIT,'checkout',commit])
            try:
                if commit in args.patches:
                    logger.info('User-defined patch: %s' % (stripbuildinfopatch))
                check_call([GIT,'apply', os.path.join(PATCHDIR,stripbuildinfopatch)])
            except subprocess.CalledProcessError:
                logger.error('Could not apply patch to strip build info. Probably it needs to be updated')
                exit(1)

            check_call(['./autogen.sh'])
            logger.info('Running configure script')
            opt = shell_join(args.opt)
            check_call(['./configure', '--disable-hardening', '--with-incompatible-bdb', '--without-cli', '--disable-tests', '--disable-ccache',
                'CPPFLAGS='+(' '.join(cppflags)),
                'CFLAGS='+opt, 'CXXFLAGS='+opt, 'LDFLAGS='+opt] + CONFIGURE_EXTRA)

            for name in args.executables:
                logger.info('Building executable %s' % name)
                target_name = os.path.join(args.tgtdir, os.path.basename(name) + '.' + commit)
                check_call([MAKE] + make_args + [name])
                shutil.copy(name, target_name)
                check_call([OBJCOPY] + OBJCOPY_ARGS + [name, target_name + '.stripped'])

            logger.info('Copying object files...')
            copy_o_files('.', commitdir_obj)

            logger.info('Performing basic analysis pass...')
            objdump_all(commitdir_obj, commitdir)

        if len(args.commitids)>1:
            logger.info('Use these commands to compare results:')
            logger.info('$ sha256sum %s/*.stripped' % (args.tgtdir))
            logger.info('$ git diff -W --word-diff %s %s' % (os.path.join(args.tgtdir,args.commitids[0]), os.path.join(args.tgtdir,args.commitids[1])))
    except Exception:
        logger.exception('Error:')

if __name__ == '__main__':
    main()
