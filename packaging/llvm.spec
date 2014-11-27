%bcond_with doxygen
%bcond_without clang

%global downloadurl http://llvm.org/%{?prerel:pre-}releases/%{version}%{?prerel:/%{prerel}}

# gold linker support
# arch list from binutils spec
%global gold_arches %ix86 x86_64
%ifarch %gold_arches
%bcond_without gold
%else
%bcond_with gold
%endif

Name:           llvm
Version:        3.5.0
Release:        0
VCS:            platform/upstream/llvm#submit/tizen/20130912.090411-0-gd860bd21c282d949117b5c9b73865809e1c5aacc
Summary:        The Low Level Virtual Machine

Group:          Development/Toolchain
License:        NCSA
URL:            http://llvm.org/
Source0:        llvm-%{version}.src.tar.gz
Source1:        cfe-%{version}.src.tar.xz
# multilib fixes
Source2:        llvm-Config-config.h
Source3:        llvm-Config-llvm-config.h
Source1001: 	llvm.manifest

BuildRequires: python-devel
BuildRequires:  bison
BuildRequires:  chrpath
BuildRequires:  flex
BuildRequires:  gcc-c++ >= 3.4
BuildRequires:  groff
BuildRequires:  libffi-devel
BuildRequires:  libtool-ltdl-devel
%if %{with gold}
BuildRequires:  binutils-devel
%endif
BuildRequires:  zip
# for doxygen documentation
%if %{with doxygen}
BuildRequires:  doxygen graphviz
%endif
Requires:       libllvm = %{version}-%{release}

%description
LLVM is a compiler infrastructure designed for compile-time,
link-time, runtime, and idle-time optimization of programs from
arbitrary programming languages.  The compiler infrastructure includes
mirror sets of programming tools as well as libraries with equivalent
functionality.


%package devel
Summary:        Libraries and header files for LLVM
Requires:       %{name} = %{version}-%{release}
Requires:       libffi-devel
Requires:       libstdc++-devel >= 3.4
Provides:       llvm-static = %{version}-%{release}
Requires(pre):         update-alternatives

%description devel
This package contains library and header files needed to develop new
native programs that use the LLVM infrastructure.




%package -n libllvm
Summary:        LLVM shared libraries

%description -n libllvm
Shared libraries for the LLVM compiler infrastructure.


%if %{with clang}
%package -n clang
Summary:        A C language family front-end for LLVM
License:        NCSA
Requires:       llvm = %{version}-%{release}
# clang requires gcc, clang++ requires libstdc++-devel
Requires:       gcc
Requires:       libstdc++-devel >= %{gcc_version}

%description -n clang
clang: noun
    1. A loud, resonant, metallic sound.
    2. The strident call of a crane or goose.
    3. C-language family front-end toolkit.

The goal of the Clang project is to create a new C, C++, Objective C
and Objective C++ front-end for the LLVM compiler. Its tools are built
as libraries and designed to be loosely-coupled and extensible.


%package -n clang-devel
Summary:        Header files for clang
Requires:       clang = %{version}-%{release}

%description -n clang-devel
This package contains header files for the Clang compiler.


%package -n clang-analyzer
Summary:        A source code analysis framework
License:        NCSA
Requires:       clang = %{version}-%{release}
# not picked up automatically since files are currently not instaled
# in standard Python hierarchies yet
Requires:       python

%description -n clang-analyzer
The Clang Static Analyzer consists of both a source code analysis
framework and a standalone tool that finds bugs in C and Objective-C
programs. The standalone tool is invoked from the command-line, and is
intended to run in tandem with a build of a project or code base.


%package -n clang-doc
Summary:        Documentation for Clang
BuildArch:      noarch
Requires:       %{name} = %{version}-%{release}

%description -n clang-doc
Documentation for the Clang compiler front-end.
%endif


%if %{with doxygen}
%package apidoc
Summary:        API documentation for LLVM
BuildArch:      noarch
Requires:       %{name}-doc = %{version}-%{release}


%description apidoc
API documentation for the LLVM compiler infrastructure.


%if %{with clang}
%package -n clang-apidoc
Summary:        API documentation for Clang
BuildArch:      noarch
Requires:       clang-doc = %{version}-%{release}


%description -n clang-apidoc
API documentation for the Clang compiler.
%endif
%endif




%prep
%setup -q -n llvm-%{version}.src %{?with_clang:-a1}
cp %{SOURCE1001} .
rm -r -f tools/clang
%if %{with clang}
mv cfe-%{version}%{?prerel}.src tools/clang
%endif




# fix ld search path
sed -i 's|/lib /usr/lib $lt_ld_extra|%{_libdir} $lt_ld_extra|' \
    ./configure


%build
# Build without -ftree-pre as a workaround for clang segfaulting on x86_64.
# https://bugzilla.redhat.com/show_bug.cgi?id=791365
%global optflags %(echo %{optflags} | sed 's/-O2 /-O2 -fno-tree-pre /')

# Disabling assertions now, rec. by pure and needed for OpenGTL
%configure \
  --prefix=%{_prefix} \
  --libdir=%{_libdir}/%{name} \
%if %{with doxygen}
  --enable-doxygen \
%endif
%if %{with gold}
  --with-binutils-include=%{_includedir} \
%endif
  --enable-targets=all \
%ifarch armv7hl armv7l
  --with-cpu=cortex-a8 \
  --with-tune=cortex-a8 \
  --with-arch=armv7-a \
  --with-float=hard \
  --with-fpu=vfpv3-d16 \
  --with-abi=aapcs-linux \
%endif
  --disable-assertions \
  --enable-debug-runtime \
  --enable-jit \
  --enable-libffi \
  --enable-shared

# FIXME file this
# configure does not properly specify libdir
sed -i 's|(PROJ_prefix)/lib|(PROJ_prefix)/%{_lib}/%{name}|g' Makefile.config

# FIXME upstream need to fix this
# llvm-config.cpp hardcodes lib in it
sed -i 's|ActiveLibDir = ActivePrefix + "/lib"|ActiveLibDir = ActivePrefix + "/%{_lib}/%{name}"|g' tools/llvm-config/llvm-config.cpp

make %{_smp_mflags} REQUIRES_RTTI=1 VERBOSE=1  OPTIMIZE_OPTION="%{optflags}"

%check
# the Koji build server does not seem to have enough RAM
# for the default 16 threads

make check LIT_ARGS="-v -j4" \
%ifarch %{arm} 
     | tee llvm-testlog-%{_arch}.txt
%else
 %{nil}
%endif

%if %{with clang}
# FIXME:
# unexpected failures on all platforms with GCC 4.7.0.
# capture logs
make -C tools/clang/test TESTARGS="-v -j4" \
     | tee clang-testlog-%{_arch}.txt
%endif

%install
make install DESTDIR=%{buildroot} \
     PROJ_docsdir=/moredocs

# multilib fixes
mv %{buildroot}%{_bindir}/llvm-config{,-%{__isa_bits}}

pushd %{buildroot}%{_includedir}/llvm/Config
mv config.h config-%{__isa_bits}.h
cp -p %{SOURCE2} config.h
mv llvm-config.h llvm-config-%{__isa_bits}.h
cp -p %{SOURCE3} llvm-config.h
popd

# Create ld.so.conf.d entry
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d
cat >> %{buildroot}%{_sysconfdir}/ld.so.conf.d/llvm-%{_arch}.conf << EOF
%{_libdir}/llvm
EOF

%if %{with clang}
# Static analyzer not installed by default:
# http://clang-analyzer.llvm.org/installation#OtherPlatforms
mkdir -p %{buildroot}%{_libdir}/clang-analyzer
# create launchers
for f in scan-{build,view}; do
  ln -s %{_libdir}/clang-analyzer/$f/$f %{buildroot}%{_bindir}/$f
done

(cd tools/clang/tools && cp -pr scan-{build,view} \
 %{buildroot}%{_libdir}/clang-analyzer/)
%endif

# Move documentation back to build directory
# 
mv %{buildroot}/moredocs .
rm -f moredocs/*.tar.gz
rm -f moredocs/ocamldoc/html/*.tar.gz

# and separate the apidoc
%if %{with doxygen}
mv moredocs/html/doxygen apidoc
mv tools/clang/docs/doxygen/html clang-apidoc
%endif

# And prepare Clang documentation
#
%if %{with clang}
mkdir clang-docs
for f in LICENSE.TXT NOTES.txt README.txt; do # TODO.txt; do
  ln tools/clang/$f clang-docs/
done
rm -rf tools/clang/docs/{doxygen*,Makefile*,*.graffle,tools}
%endif


file %{buildroot}/%{_bindir}/* | awk -F: '$2~/ELF/{print $1}' | xargs -r chrpath -d
file %{buildroot}/%{_libdir}/llvm/*.so | awk -F: '$2~/ELF/{print $1}' | xargs -r chrpath -d
#chrpath -d %%{buildroot}/%%{_libexecdir}/clang-cc

# Get rid of erroneously installed example files.
rm %{buildroot}%{_libdir}/%{name}/*LLVMHello.*

# FIXME file this bug
sed -i 's,ABS_RUN_DIR/lib",ABS_RUN_DIR/%{_lib}/%{name}",' \
  %{buildroot}%{_bindir}/llvm-config-%{__isa_bits}

chmod -x %{buildroot}%{_libdir}/%{name}/*.a

# remove documentation makefiles:
# they require the build directory to work
find examples -name 'Makefile' | xargs -0r rm -f
#rm %{buildroot}/usr/lib/llvm/libLLVM-3.5svn.so


cd $RPM_BUILD_DIR

%remove_docs


%post -n libllvm -p /sbin/ldconfig

%postun -n libllvm -p /sbin/ldconfig

%if %{with clang}
%post -n clang -p /sbin/ldconfig

%postun -n clang -p /sbin/ldconfig
%endif

%posttrans devel
# link llvm-config to the platform-specific file;
# use ISA bits as priority so that 64-bit is preferred
# over 32-bit if both are installed
/usr/sbin/update-alternatives \
  --install \
  %{_bindir}/llvm-config \
  llvm-config \
  %{_bindir}/llvm-config-%{__isa_bits} \
  %{__isa_bits}

%postun devel
if [ $1 -eq 0 ]; then
  /usr/sbin/update-alternatives --remove llvm-config \
    %{_bindir}/llvm-config-%{__isa_bits}
fi
exit 0


%files
%manifest %{name}.manifest
%defattr(-,root,root,-)
%license LICENSE.TXT
%{_bindir}/bugpoint
%{_bindir}/llc
%{_bindir}/lli
%exclude %{_bindir}/llvm-config-%{__isa_bits}
%{_bindir}/llvm*
%{_bindir}/macho-dump
%{_bindir}/opt
%{_bindir}/FileCheck
%{_bindir}/count
%{_bindir}/not
%{_bindir}/lli-child-target

%files devel
%manifest %{name}.manifest
%defattr(-,root,root,-)
%{_bindir}/llvm-config-%{__isa_bits}
%{_includedir}/%{name}
%{_includedir}/%{name}-c
%{_libdir}/%{name}/*.a
%{_datadir}/%{name}/cmake/*.cmake

%files -n libllvm
%manifest %{name}.manifest
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/ld.so.conf.d/llvm-%{_arch}.conf
%dir %{_libdir}/%{name}
%if %{with clang}
%exclude %{_libdir}/%{name}/libclang.so
%endif
%{_libdir}/%{name}/*.so

%if %{with clang}
%files -n clang
%manifest %{name}.manifest
%defattr(-,root,root,-)
%{_bindir}/clang*
%{_bindir}/c-index-test
%{_libdir}/%{name}/libclang.so
%{_prefix}/lib/clang

%files -n clang-devel
%manifest %{name}.manifest
%defattr(-,root,root,-)
%{_includedir}/clang
%{_includedir}/clang-c

%files -n clang-analyzer
%manifest %{name}.manifest
%defattr(-,root,root,-)
%{_bindir}/scan-build
%{_bindir}/scan-view
%{_libdir}/clang-analyzer
%endif


%if %{with doxygen}
%files apidoc
%manifest %{name}.manifest
%defattr(-,root,root,-)
%doc apidoc/*

%if %{with clang}
%files -n clang-apidoc
%manifest %{name}.manifest
%defattr(-,root,root,-)
%doc clang-apidoc/*
%endif
%endif

