╔═══════════════════════════════════════════════════════════════╗
║ L9 10X Deploy (GitHub SSOT + Env Sync)                      ║
╚═══════════════════════════════════════════════════════════════╝

[LOCAL] Repo:   /Users/ib-mac/Projects/l9
[LOCAL] Branch: main
[LOCAL] Commit: 31a84f4b

[LOCAL] Git status:
 M scripts/deployment/10X_Deploy_Script.sh

 = .env.vps.template already up-to-date
[main 81a78fbc] 10X_Deploy_Script.sh
 1 file changed, 35 insertions(+), 40 deletions(-)
Enumerating objects: 9, done.
Counting objects: 100% (9/9), done.
Delta compression using up to 8 threads
Compressing objects: 100% (5/5), done.
Writing objects: 100% (5/5), 1.06 KiB | 1.06 MiB/s, done.
Total 5 (delta 4), reused 0 (delta 0), pack-reused 0 (from 0)
remote: Resolving deltas: 100% (4/4), completed with 4 local objects.
To https://github.com/cryptoxdog/L9.git
   31a84f4b..81a78fbc  HEAD -> main
[VPS] Hard reset to origin/main (SSOT)
From github.com:cryptoxdog/L9
 * branch              main       -> FETCH_HEAD
   31a84f4b..81a78fbc  main       -> origin/main
HEAD is now at 81a78fbc 10X_Deploy_Script.sh
[ENV] Syncing .env.vps -> c1:/opt/l9/.env
 ✅ Env synced (sha256 match)
[VPS] Rebuild stack (base + prod overlay) no-cache=true
time="2026-02-06T08:17:02Z" level=warning msg="The \"GRAFANA_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2026-02-06T08:17:03Z" level=warning msg="The \"GRAFANA_PASSWORD\" variable is not set. Defaulting to a blank string."
 Image ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0 Building 
 Image ghcr.io/cryptoxdog/l9-api:4.1.0 Building 
 Image ghcr.io/cryptoxdog/l9-api:4.1.0 Building 
#1 [internal] load local bake definitions
#1 reading from stdin 2.08kB done
#1 DONE 0.0s

#2 [l9-bootstrap internal] load build definition from Dockerfile
#2 transferring dockerfile: 4.87kB done
#2 DONE 0.0s

#3 [l9-mcp-memory internal] load build definition from Dockerfile.mcp-memory
#3 transferring dockerfile: 5.06kB done
#3 DONE 0.0s

#4 [l9-mcp-memory internal] load metadata for docker.io/library/python:3.12-slim
#4 DONE 1.7s

#5 [l9-bootstrap internal] load .dockerignore
#5 transferring context: 480B done
#5 DONE 0.0s

#6 [l9-bootstrap base 1/4] FROM docker.io/library/python:3.12-slim@sha256:43e4d702bbfe3bd6d5b743dc571b67c19121302eb172951a9b7b0149783a1c21
#6 resolve docker.io/library/python:3.12-slim@sha256:43e4d702bbfe3bd6d5b743dc571b67c19121302eb172951a9b7b0149783a1c21 0.0s done
#6 sha256:43e4d702bbfe3bd6d5b743dc571b67c19121302eb172951a9b7b0149783a1c21 10.37kB / 10.37kB done
#6 sha256:48006ff57afe15f247ad3da166e9487da0f66a94adbc92810b0e189382d79246 1.75kB / 1.75kB done
#6 sha256:b3b92273ebb48091c16ef5f9cc1fdde40d18c7365ec38df5e9f900a2aeb3db1c 5.66kB / 5.66kB done
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 0B / 29.78MB 0.1s
#6 sha256:690eaffcf0e9a6e579bf82062d0d78590bd1bc000a309b8e76ff4ca460bcdb6f 0B / 1.29MB 0.1s
#6 sha256:9395e1d7be50336f1932db3e6904cc05ad5b727731f03ae218688af3f525ec30 0B / 12.11MB 0.1s
#6 sha256:43e4d702bbfe3bd6d5b743dc571b67c19121302eb172951a9b7b0149783a1c21 10.37kB / 10.37kB done
#6 sha256:48006ff57afe15f247ad3da166e9487da0f66a94adbc92810b0e189382d79246 1.75kB / 1.75kB done
#6 sha256:b3b92273ebb48091c16ef5f9cc1fdde40d18c7365ec38df5e9f900a2aeb3db1c 5.66kB / 5.66kB done
#6 ...

#7 [l9-mcp-memory internal] load build context
#7 transferring context: 7.30MB 0.3s done
#7 DONE 0.4s

#6 [l9-bootstrap base 1/4] FROM docker.io/library/python:3.12-slim@sha256:43e4d702bbfe3bd6d5b743dc571b67c19121302eb172951a9b7b0149783a1c21
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 2.10MB / 29.78MB 0.5s
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 6.29MB / 29.78MB 0.6s
#6 sha256:690eaffcf0e9a6e579bf82062d0d78590bd1bc000a309b8e76ff4ca460bcdb6f 1.29MB / 1.29MB 0.6s done
#6 sha256:4948ee38326639b0ee49566ec9752e0500fde95ffa7a4771067a7856446029fe 0B / 251B 0.6s
#6 ...

#8 [l9-bootstrap internal] load build context
#8 transferring context: 31.95MB 0.6s done
#8 DONE 0.7s

#6 [l9-bootstrap base 1/4] FROM docker.io/library/python:3.12-slim@sha256:43e4d702bbfe3bd6d5b743dc571b67c19121302eb172951a9b7b0149783a1c21
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 12.58MB / 29.78MB 0.8s
#6 sha256:9395e1d7be50336f1932db3e6904cc05ad5b727731f03ae218688af3f525ec30 7.34MB / 12.11MB 0.8s
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 20.97MB / 29.78MB 1.0s
#6 sha256:9395e1d7be50336f1932db3e6904cc05ad5b727731f03ae218688af3f525ec30 12.11MB / 12.11MB 0.9s done
#6 sha256:4948ee38326639b0ee49566ec9752e0500fde95ffa7a4771067a7856446029fe 251B / 251B 0.9s done
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 26.21MB / 29.78MB 1.1s
#6 sha256:9395e1d7be50336f1932db3e6904cc05ad5b727731f03ae218688af3f525ec30 12.11MB / 12.11MB 0.9s done
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 29.78MB / 29.78MB 1.2s done
#6 sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 29.78MB / 29.78MB 1.2s done
#6 extracting sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 0.1s
#6 extracting sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 2.0s done
#6 extracting sha256:0c8d55a45c0dc58de60579b9cc5b708de9e7957f4591fc7de941b67c7e245da0 2.0s done
#6 extracting sha256:690eaffcf0e9a6e579bf82062d0d78590bd1bc000a309b8e76ff4ca460bcdb6f 0.1s
#6 extracting sha256:690eaffcf0e9a6e579bf82062d0d78590bd1bc000a309b8e76ff4ca460bcdb6f 0.2s done
#6 extracting sha256:9395e1d7be50336f1932db3e6904cc05ad5b727731f03ae218688af3f525ec30 0.1s
#6 extracting sha256:9395e1d7be50336f1932db3e6904cc05ad5b727731f03ae218688af3f525ec30 1.1s done
#6 extracting sha256:4948ee38326639b0ee49566ec9752e0500fde95ffa7a4771067a7856446029fe done
#6 DONE 4.9s

#9 [l9-bootstrap base 2/4] WORKDIR /app
#9 DONE 0.3s

#10 [l9-api base 3/4] RUN apt-get update && apt-get install -y --no-install-recommends     curl     ca-certificates     && rm -rf /var/lib/apt/lists/*
#10 0.427 Hit:1 http://deb.debian.org/debian trixie InRelease
#10 0.427 Get:2 http://deb.debian.org/debian trixie-updates InRelease [47.3 kB]
#10 0.431 Get:3 http://deb.debian.org/debian-security trixie-security InRelease [43.4 kB]
#10 0.465 Get:4 http://deb.debian.org/debian trixie/main amd64 Packages [9670 kB]
#10 0.588 Get:5 http://deb.debian.org/debian trixie-updates/main amd64 Packages [5412 B]
#10 0.588 Get:6 http://deb.debian.org/debian-security trixie-security/main amd64 Packages [100 kB]
#10 1.179 Fetched 9867 kB in 1s (12.4 MB/s)
#10 1.179 Reading package lists...
#10 1.621 Reading package lists...
#10 2.097 Building dependency tree...
#10 2.213 Reading state information...
#10 2.342 ca-certificates is already the newest version (20250419).
#10 2.342 The following additional packages will be installed:
#10 2.342   libbrotli1 libcom-err2 libcurl4t64 libgnutls30t64 libgssapi-krb5-2 libidn2-0
#10 2.343   libk5crypto3 libkeyutils1 libkrb5-3 libkrb5support0 libldap2 libnghttp2-14
#10 2.343   libnghttp3-9 libp11-kit0 libpsl5t64 librtmp1 libsasl2-2 libsasl2-modules-db
#10 2.343   libssh2-1t64 libtasn1-6 libunistring5
#10 2.343 Suggested packages:
#10 2.343   gnutls-bin krb5-doc krb5-user
#10 2.343 Recommended packages:
#10 2.343   bash-completion krb5-locales libldap-common publicsuffix libsasl2-modules
#10 2.513 The following NEW packages will be installed:
#10 2.513   curl libbrotli1 libcom-err2 libcurl4t64 libgnutls30t64 libgssapi-krb5-2
#10 2.513   libidn2-0 libk5crypto3 libkeyutils1 libkrb5-3 libkrb5support0 libldap2
#10 2.513   libnghttp2-14 libnghttp3-9 libp11-kit0 libpsl5t64 librtmp1 libsasl2-2
#10 2.513   libsasl2-modules-db libssh2-1t64 libtasn1-6 libunistring5
#10 2.563 0 upgraded, 22 newly installed, 0 to remove and 0 not upgraded.
#10 2.563 Need to get 4883 kB of archives.
#10 2.563 After this operation, 14.7 MB of additional disk space will be used.
#10 2.563 Get:1 http://deb.debian.org/debian trixie/main amd64 libbrotli1 amd64 1.1.0-2+b7 [307 kB]
#10 2.590 Get:2 http://deb.debian.org/debian trixie/main amd64 libkrb5support0 amd64 1.21.3-5 [33.0 kB]
#10 2.591 Get:3 http://deb.debian.org/debian trixie/main amd64 libcom-err2 amd64 1.47.2-3+b7 [25.0 kB]
#10 2.592 Get:4 http://deb.debian.org/debian trixie/main amd64 libk5crypto3 amd64 1.21.3-5 [81.5 kB]
#10 2.592 Get:5 http://deb.debian.org/debian trixie/main amd64 libkeyutils1 amd64 1.6.3-6 [9456 B]
#10 2.593 Get:6 http://deb.debian.org/debian trixie/main amd64 libkrb5-3 amd64 1.21.3-5 [326 kB]
#10 2.599 Get:7 http://deb.debian.org/debian trixie/main amd64 libgssapi-krb5-2 amd64 1.21.3-5 [138 kB]
#10 2.601 Get:8 http://deb.debian.org/debian trixie/main amd64 libunistring5 amd64 1.3-2 [477 kB]
#10 2.605 Get:9 http://deb.debian.org/debian trixie/main amd64 libidn2-0 amd64 2.3.8-2 [109 kB]
#10 2.607 Get:10 http://deb.debian.org/debian trixie/main amd64 libsasl2-modules-db amd64 2.1.28+dfsg1-9 [19.8 kB]
#10 2.608 Get:11 http://deb.debian.org/debian trixie/main amd64 libsasl2-2 amd64 2.1.28+dfsg1-9 [57.5 kB]
#10 2.608 Get:12 http://deb.debian.org/debian trixie/main amd64 libldap2 amd64 2.6.10+dfsg-1 [194 kB]
#10 2.609 Get:13 http://deb.debian.org/debian trixie/main amd64 libnghttp2-14 amd64 1.64.0-1.1 [76.0 kB]
#10 2.611 Get:14 http://deb.debian.org/debian trixie/main amd64 libnghttp3-9 amd64 1.8.0-1 [67.7 kB]
#10 2.612 Get:15 http://deb.debian.org/debian trixie/main amd64 libpsl5t64 amd64 0.21.2-1.1+b1 [57.2 kB]
#10 2.613 Get:16 http://deb.debian.org/debian trixie/main amd64 libp11-kit0 amd64 0.25.5-3 [425 kB]
#10 2.616 Get:17 http://deb.debian.org/debian trixie/main amd64 libtasn1-6 amd64 4.20.0-2 [49.9 kB]
#10 2.621 Get:18 http://deb.debian.org/debian trixie/main amd64 libgnutls30t64 amd64 3.8.9-3+deb13u1 [1466 kB]
#10 2.629 Get:19 http://deb.debian.org/debian trixie/main amd64 librtmp1 amd64 2.4+20151223.gitfa8646d.1-2+b5 [58.8 kB]
#10 2.630 Get:20 http://deb.debian.org/debian trixie/main amd64 libssh2-1t64 amd64 1.11.1-1 [245 kB]
#10 2.632 Get:21 http://deb.debian.org/debian trixie/main amd64 libcurl4t64 amd64 8.14.1-2+deb13u2 [391 kB]
#10 2.635 Get:22 http://deb.debian.org/debian trixie/main amd64 curl amd64 8.14.1-2+deb13u2 [270 kB]
#10 2.864 debconf: unable to initialize frontend: Dialog
#10 2.864 debconf: (TERM is not set, so the dialog frontend is not usable.)
#10 2.864 debconf: falling back to frontend: Readline
#10 2.865 debconf: unable to initialize frontend: Readline
#10 2.865 debconf: (Can't locate Term/ReadLine.pm in @INC (you may need to install the Term::ReadLine module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.40.1 /usr/local/share/perl/5.40.1 /usr/lib/x86_64-linux-gnu/perl5/5.40 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.40 /usr/share/perl/5.40 /usr/local/lib/site_perl) at /usr/share/perl5/Debconf/FrontEnd/Readline.pm line 8, <STDIN> line 22.)
#10 2.865 debconf: falling back to frontend: Teletype
#10 2.876 debconf: unable to initialize frontend: Teletype
#10 2.876 debconf: (This frontend requires a controlling tty.)
#10 2.876 debconf: falling back to frontend: Noninteractive
#10 3.405 Fetched 4883 kB in 0s (43.8 MB/s)
#10 3.444 Selecting previously unselected package libbrotli1:amd64.
(Reading database ... 5645 files and directories currently installed.)
#10 3.455 Preparing to unpack .../00-libbrotli1_1.1.0-2+b7_amd64.deb ...
#10 3.463 Unpacking libbrotli1:amd64 (1.1.0-2+b7) ...
#10 3.528 Selecting previously unselected package libkrb5support0:amd64.
#10 3.530 Preparing to unpack .../01-libkrb5support0_1.21.3-5_amd64.deb ...
#10 3.532 Unpacking libkrb5support0:amd64 (1.21.3-5) ...
#10 3.568 Selecting previously unselected package libcom-err2:amd64.
#10 3.570 Preparing to unpack .../02-libcom-err2_1.47.2-3+b7_amd64.deb ...
#10 3.573 Unpacking libcom-err2:amd64 (1.47.2-3+b7) ...
#10 3.616 Selecting previously unselected package libk5crypto3:amd64.
#10 3.617 Preparing to unpack .../03-libk5crypto3_1.21.3-5_amd64.deb ...
#10 3.621 Unpacking libk5crypto3:amd64 (1.21.3-5) ...
#10 3.668 Selecting previously unselected package libkeyutils1:amd64.
#10 3.670 Preparing to unpack .../04-libkeyutils1_1.6.3-6_amd64.deb ...
#10 3.673 Unpacking libkeyutils1:amd64 (1.6.3-6) ...
#10 3.714 Selecting previously unselected package libkrb5-3:amd64.
#10 3.716 Preparing to unpack .../05-libkrb5-3_1.21.3-5_amd64.deb ...
#10 3.719 Unpacking libkrb5-3:amd64 (1.21.3-5) ...
#10 3.796 Selecting previously unselected package libgssapi-krb5-2:amd64.
#10 3.798 Preparing to unpack .../06-libgssapi-krb5-2_1.21.3-5_amd64.deb ...
#10 3.801 Unpacking libgssapi-krb5-2:amd64 (1.21.3-5) ...
#10 3.859 Selecting previously unselected package libunistring5:amd64.
#10 3.862 Preparing to unpack .../07-libunistring5_1.3-2_amd64.deb ...
#10 3.865 Unpacking libunistring5:amd64 (1.3-2) ...
#10 3.955 Selecting previously unselected package libidn2-0:amd64.
#10 3.957 Preparing to unpack .../08-libidn2-0_2.3.8-2_amd64.deb ...
#10 3.961 Unpacking libidn2-0:amd64 (2.3.8-2) ...
#10 4.001 Selecting previously unselected package libsasl2-modules-db:amd64.
#10 4.003 Preparing to unpack .../09-libsasl2-modules-db_2.1.28+dfsg1-9_amd64.deb ...
#10 4.005 Unpacking libsasl2-modules-db:amd64 (2.1.28+dfsg1-9) ...
#10 4.041 Selecting previously unselected package libsasl2-2:amd64.
#10 4.043 Preparing to unpack .../10-libsasl2-2_2.1.28+dfsg1-9_amd64.deb ...
#10 4.049 Unpacking libsasl2-2:amd64 (2.1.28+dfsg1-9) ...
#10 4.096 Selecting previously unselected package libldap2:amd64.
#10 4.098 Preparing to unpack .../11-libldap2_2.6.10+dfsg-1_amd64.deb ...
#10 4.102 Unpacking libldap2:amd64 (2.6.10+dfsg-1) ...
#10 4.165 Selecting previously unselected package libnghttp2-14:amd64.
#10 4.166 Preparing to unpack .../12-libnghttp2-14_1.64.0-1.1_amd64.deb ...
#10 4.170 Unpacking libnghttp2-14:amd64 (1.64.0-1.1) ...
#10 4.220 Selecting previously unselected package libnghttp3-9:amd64.
#10 4.222 Preparing to unpack .../13-libnghttp3-9_1.8.0-1_amd64.deb ...
#10 4.226 Unpacking libnghttp3-9:amd64 (1.8.0-1) ...
#10 4.272 Selecting previously unselected package libpsl5t64:amd64.
#10 4.275 Preparing to unpack .../14-libpsl5t64_0.21.2-1.1+b1_amd64.deb ...
#10 4.280 Unpacking libpsl5t64:amd64 (0.21.2-1.1+b1) ...
#10 4.327 Selecting previously unselected package libp11-kit0:amd64.
#10 4.327 Preparing to unpack .../15-libp11-kit0_0.25.5-3_amd64.deb ...
#10 4.330 Unpacking libp11-kit0:amd64 (0.25.5-3) ...
#10 4.407 Selecting previously unselected package libtasn1-6:amd64.
#10 4.409 Preparing to unpack .../16-libtasn1-6_4.20.0-2_amd64.deb ...
#10 4.413 Unpacking libtasn1-6:amd64 (4.20.0-2) ...
#10 4.458 Selecting previously unselected package libgnutls30t64:amd64.
#10 4.460 Preparing to unpack .../17-libgnutls30t64_3.8.9-3+deb13u1_amd64.deb ...
#10 4.463 Unpacking libgnutls30t64:amd64 (3.8.9-3+deb13u1) ...
#10 4.573 Selecting previously unselected package librtmp1:amd64.
#10 4.575 Preparing to unpack .../18-librtmp1_2.4+20151223.gitfa8646d.1-2+b5_amd64.deb ...
#10 4.579 Unpacking librtmp1:amd64 (2.4+20151223.gitfa8646d.1-2+b5) ...
#10 4.623 Selecting previously unselected package libssh2-1t64:amd64.
#10 4.624 Preparing to unpack .../19-libssh2-1t64_1.11.1-1_amd64.deb ...
#10 4.628 Unpacking libssh2-1t64:amd64 (1.11.1-1) ...
#10 4.689 Selecting previously unselected package libcurl4t64:amd64.
#10 4.690 Preparing to unpack .../20-libcurl4t64_8.14.1-2+deb13u2_amd64.deb ...
#10 4.695 Unpacking libcurl4t64:amd64 (8.14.1-2+deb13u2) ...
#10 4.764 Selecting previously unselected package curl.
#10 4.764 Preparing to unpack .../21-curl_8.14.1-2+deb13u2_amd64.deb ...
#10 4.767 Unpacking curl (8.14.1-2+deb13u2) ...
#10 4.826 Setting up libkeyutils1:amd64 (1.6.3-6) ...
#10 4.835 Setting up libbrotli1:amd64 (1.1.0-2+b7) ...
#10 4.843 Setting up libnghttp2-14:amd64 (1.64.0-1.1) ...
#10 4.851 Setting up libcom-err2:amd64 (1.47.2-3+b7) ...
#10 4.860 Setting up libkrb5support0:amd64 (1.21.3-5) ...
#10 4.869 Setting up libsasl2-modules-db:amd64 (2.1.28+dfsg1-9) ...
#10 4.877 Setting up libp11-kit0:amd64 (0.25.5-3) ...
#10 4.886 Setting up libunistring5:amd64 (1.3-2) ...
#10 4.894 Setting up libk5crypto3:amd64 (1.21.3-5) ...
#10 4.902 Setting up libsasl2-2:amd64 (2.1.28+dfsg1-9) ...
#10 4.910 Setting up libnghttp3-9:amd64 (1.8.0-1) ...
#10 4.918 Setting up libtasn1-6:amd64 (4.20.0-2) ...
#10 4.927 Setting up libkrb5-3:amd64 (1.21.3-5) ...
#10 4.936 Setting up libssh2-1t64:amd64 (1.11.1-1) ...
#10 4.945 Setting up libldap2:amd64 (2.6.10+dfsg-1) ...
#10 4.954 Setting up libidn2-0:amd64 (2.3.8-2) ...
#10 4.964 Setting up libgssapi-krb5-2:amd64 (1.21.3-5) ...
#10 4.976 Setting up libgnutls30t64:amd64 (3.8.9-3+deb13u1) ...
#10 4.986 Setting up libpsl5t64:amd64 (0.21.2-1.1+b1) ...
#10 4.994 Setting up librtmp1:amd64 (2.4+20151223.gitfa8646d.1-2+b5) ...
#10 5.003 Setting up libcurl4t64:amd64 (8.14.1-2+deb13u2) ...
#10 5.013 Setting up curl (8.14.1-2+deb13u2) ...
#10 5.022 Processing triggers for libc-bin (2.41-12+deb13u1) ...
#10 DONE 5.2s

#11 [l9-mcp-memory base 3/4] RUN apt-get update && apt-get install -y --no-install-recommends     curl     postgresql-client     ca-certificates     && rm -rf /var/lib/apt/lists/*
#11 0.432 Hit:1 http://deb.debian.org/debian trixie InRelease
#11 0.433 Get:2 http://deb.debian.org/debian trixie-updates InRelease [47.3 kB]
#11 0.437 Get:3 http://deb.debian.org/debian-security trixie-security InRelease [43.4 kB]
#11 0.467 Get:4 http://deb.debian.org/debian trixie/main amd64 Packages [9670 kB]
#11 0.606 Get:5 http://deb.debian.org/debian trixie-updates/main amd64 Packages [5412 B]
#11 0.608 Get:6 http://deb.debian.org/debian-security trixie-security/main amd64 Packages [100 kB]
#11 1.195 Fetched 9867 kB in 1s (12.2 MB/s)
#11 1.195 Reading package lists...
#11 1.699 Reading package lists...
#11 2.190 Building dependency tree...
#11 2.319 Reading state information...
#11 2.450 ca-certificates is already the newest version (20250419).
#11 2.450 The following additional packages will be installed:
#11 2.451   libbrotli1 libcom-err2 libcurl4t64 libgdbm-compat4t64 libgnutls30t64
#11 2.451   libgssapi-krb5-2 libidn2-0 libk5crypto3 libkeyutils1 libkrb5-3
#11 2.451   libkrb5support0 libldap2 libnghttp2-14 libnghttp3-9 libp11-kit0 libperl5.40
#11 2.451   libpq5 libpsl5t64 librtmp1 libsasl2-2 libsasl2-modules-db libssh2-1t64
#11 2.451   libtasn1-6 libunistring5 perl perl-modules-5.40 postgresql-client-17
#11 2.451   postgresql-client-common sensible-utils
#11 2.452 Suggested packages:
#11 2.452   gnutls-bin krb5-doc krb5-user perl-doc libterm-readline-gnu-perl
#11 2.452   | libterm-readline-perl-perl make libtap-harness-archive-perl postgresql-17
#11 2.452   postgresql-doc-17
#11 2.452 Recommended packages:
#11 2.452   bash-completion krb5-locales libldap-common publicsuffix libsasl2-modules
#11 2.617 The following NEW packages will be installed:
#11 2.618   curl libbrotli1 libcom-err2 libcurl4t64 libgdbm-compat4t64 libgnutls30t64
#11 2.618   libgssapi-krb5-2 libidn2-0 libk5crypto3 libkeyutils1 libkrb5-3
#11 2.618   libkrb5support0 libldap2 libnghttp2-14 libnghttp3-9 libp11-kit0 libperl5.40
#11 2.618   libpq5 libpsl5t64 librtmp1 libsasl2-2 libsasl2-modules-db libssh2-1t64
#11 2.618   libtasn1-6 libunistring5 perl perl-modules-5.40 postgresql-client
#11 2.619   postgresql-client-17 postgresql-client-common sensible-utils
#11 2.657 0 upgraded, 31 newly installed, 0 to remove and 0 not upgraded.
#11 2.657 Need to get 14.9 MB of archives.
#11 2.657 After this operation, 78.1 MB of additional disk space will be used.
#11 2.657 Get:1 http://deb.debian.org/debian trixie/main amd64 sensible-utils all 0.0.25 [25.0 kB]
#11 2.665 Get:2 http://deb.debian.org/debian trixie/main amd64 perl-modules-5.40 all 5.40.1-6 [3019 kB]
#11 2.712 Get:3 http://deb.debian.org/debian trixie/main amd64 libgdbm-compat4t64 amd64 1.24-2 [50.3 kB]
#11 2.723 Get:4 http://deb.debian.org/debian trixie/main amd64 libperl5.40 amd64 5.40.1-6 [4341 kB]
#11 2.755 Get:5 http://deb.debian.org/debian trixie/main amd64 perl amd64 5.40.1-6 [267 kB]
#11 2.758 Get:6 http://deb.debian.org/debian trixie/main amd64 libbrotli1 amd64 1.1.0-2+b7 [307 kB]
#11 2.761 Get:7 http://deb.debian.org/debian trixie/main amd64 libkrb5support0 amd64 1.21.3-5 [33.0 kB]
#11 2.762 Get:8 http://deb.debian.org/debian trixie/main amd64 libcom-err2 amd64 1.47.2-3+b7 [25.0 kB]
#11 2.765 Get:9 http://deb.debian.org/debian trixie/main amd64 libk5crypto3 amd64 1.21.3-5 [81.5 kB]
#11 2.766 Get:10 http://deb.debian.org/debian trixie/main amd64 libkeyutils1 amd64 1.6.3-6 [9456 B]
#11 2.766 Get:11 http://deb.debian.org/debian trixie/main amd64 libkrb5-3 amd64 1.21.3-5 [326 kB]
#11 2.769 Get:12 http://deb.debian.org/debian trixie/main amd64 libgssapi-krb5-2 amd64 1.21.3-5 [138 kB]
#11 2.770 Get:13 http://deb.debian.org/debian trixie/main amd64 libunistring5 amd64 1.3-2 [477 kB]
#11 2.774 Get:14 http://deb.debian.org/debian trixie/main amd64 libidn2-0 amd64 2.3.8-2 [109 kB]
#11 2.775 Get:15 http://deb.debian.org/debian trixie/main amd64 libsasl2-modules-db amd64 2.1.28+dfsg1-9 [19.8 kB]
#11 2.775 Get:16 http://deb.debian.org/debian trixie/main amd64 libsasl2-2 amd64 2.1.28+dfsg1-9 [57.5 kB]
#11 2.776 Get:17 http://deb.debian.org/debian trixie/main amd64 libldap2 amd64 2.6.10+dfsg-1 [194 kB]
#11 2.778 Get:18 http://deb.debian.org/debian trixie/main amd64 libnghttp2-14 amd64 1.64.0-1.1 [76.0 kB]
#11 2.780 Get:19 http://deb.debian.org/debian trixie/main amd64 libnghttp3-9 amd64 1.8.0-1 [67.7 kB]
#11 2.783 Get:20 http://deb.debian.org/debian trixie/main amd64 libpsl5t64 amd64 0.21.2-1.1+b1 [57.2 kB]
#11 2.783 Get:21 http://deb.debian.org/debian trixie/main amd64 libp11-kit0 amd64 0.25.5-3 [425 kB]
#11 2.786 Get:22 http://deb.debian.org/debian trixie/main amd64 libtasn1-6 amd64 4.20.0-2 [49.9 kB]
#11 2.787 Get:23 http://deb.debian.org/debian trixie/main amd64 libgnutls30t64 amd64 3.8.9-3+deb13u1 [1466 kB]
#11 2.798 Get:24 http://deb.debian.org/debian trixie/main amd64 librtmp1 amd64 2.4+20151223.gitfa8646d.1-2+b5 [58.8 kB]
#11 2.799 Get:25 http://deb.debian.org/debian trixie/main amd64 libssh2-1t64 amd64 1.11.1-1 [245 kB]
#11 2.801 Get:26 http://deb.debian.org/debian trixie/main amd64 libcurl4t64 amd64 8.14.1-2+deb13u2 [391 kB]
#11 2.805 Get:27 http://deb.debian.org/debian trixie/main amd64 curl amd64 8.14.1-2+deb13u2 [270 kB]
#11 2.806 Get:28 http://deb.debian.org/debian trixie/main amd64 libpq5 amd64 17.7-0+deb13u1 [228 kB]
#11 2.808 Get:29 http://deb.debian.org/debian trixie/main amd64 postgresql-client-common all 278 [47.1 kB]
#11 2.809 Get:30 http://deb.debian.org/debian trixie/main amd64 postgresql-client-17 amd64 17.7-0+deb13u1 [2045 kB]
#11 2.830 Get:31 http://deb.debian.org/debian trixie/main amd64 postgresql-client all 17+278 [14.0 kB]
#11 3.022 debconf: unable to initialize frontend: Dialog
#11 3.022 debconf: (TERM is not set, so the dialog frontend is not usable.)
#11 3.023 debconf: falling back to frontend: Readline
#11 3.023 debconf: unable to initialize frontend: Readline
#11 3.023 debconf: (Can't locate Term/ReadLine.pm in @INC (you may need to install the Term::ReadLine module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.40.1 /usr/local/share/perl/5.40.1 /usr/lib/x86_64-linux-gnu/perl5/5.40 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.40 /usr/share/perl/5.40 /usr/local/lib/site_perl) at /usr/share/perl5/Debconf/FrontEnd/Readline.pm line 8, <STDIN> line 31.)
#11 3.023 debconf: falling back to frontend: Teletype
#11 3.032 debconf: unable to initialize frontend: Teletype
#11 3.032 debconf: (This frontend requires a controlling tty.)
#11 3.032 debconf: falling back to frontend: Noninteractive
#11 4.035 Fetched 14.9 MB in 0s (74.7 MB/s)
#11 4.071 Selecting previously unselected package sensible-utils.
(Reading database ... 5645 files and directories currently installed.)
#11 4.082 Preparing to unpack .../00-sensible-utils_0.0.25_all.deb ...
#11 4.085 Unpacking sensible-utils (0.0.25) ...
#11 4.138 Selecting previously unselected package perl-modules-5.40.
#11 4.140 Preparing to unpack .../01-perl-modules-5.40_5.40.1-6_all.deb ...
#11 4.143 Unpacking perl-modules-5.40 (5.40.1-6) ...
#11 4.614 Selecting previously unselected package libgdbm-compat4t64:amd64.
#11 4.616 Preparing to unpack .../02-libgdbm-compat4t64_1.24-2_amd64.deb ...
#11 4.622 Unpacking libgdbm-compat4t64:amd64 (1.24-2) ...
#11 4.666 Selecting previously unselected package libperl5.40:amd64.
#11 4.668 Preparing to unpack .../03-libperl5.40_5.40.1-6_amd64.deb ...
#11 4.672 Unpacking libperl5.40:amd64 (5.40.1-6) ...
#11 5.104 Selecting previously unselected package perl.
#11 5.109 Preparing to unpack .../04-perl_5.40.1-6_amd64.deb ...
#11 5.114 Unpacking perl (5.40.1-6) ...
#11 5.238 Selecting previously unselected package libbrotli1:amd64.
#11 5.244 Preparing to unpack .../05-libbrotli1_1.1.0-2+b7_amd64.deb ...
#11 5.248 Unpacking libbrotli1:amd64 (1.1.0-2+b7) ...
#11 5.327 Selecting previously unselected package libkrb5support0:amd64.
#11 5.330 Preparing to unpack .../06-libkrb5support0_1.21.3-5_amd64.deb ...
#11 5.333 Unpacking libkrb5support0:amd64 (1.21.3-5) ...
#11 5.374 Selecting previously unselected package libcom-err2:amd64.
#11 5.376 Preparing to unpack .../07-libcom-err2_1.47.2-3+b7_amd64.deb ...
#11 5.379 Unpacking libcom-err2:amd64 (1.47.2-3+b7) ...
#11 5.419 Selecting previously unselected package libk5crypto3:amd64.
#11 5.421 Preparing to unpack .../08-libk5crypto3_1.21.3-5_amd64.deb ...
#11 5.424 Unpacking libk5crypto3:amd64 (1.21.3-5) ...
#11 5.474 Selecting previously unselected package libkeyutils1:amd64.
#11 5.476 Preparing to unpack .../09-libkeyutils1_1.6.3-6_amd64.deb ...
#11 5.479 Unpacking libkeyutils1:amd64 (1.6.3-6) ...
#11 5.521 Selecting previously unselected package libkrb5-3:amd64.
#11 5.523 Preparing to unpack .../10-libkrb5-3_1.21.3-5_amd64.deb ...
#11 5.527 Unpacking libkrb5-3:amd64 (1.21.3-5) ...
#11 5.603 Selecting previously unselected package libgssapi-krb5-2:amd64.
#11 ...

#12 [l9-api base 4/4] RUN useradd -m -u 1000 l9user &&     mkdir -p /app/data/.l9/gmail/attachments &&     chown -R l9user:l9user /app
#12 DONE 0.4s

#13 [l9-bootstrap production 1/4] COPY requirements-docker.txt /app/
#13 DONE 0.0s

#11 [l9-mcp-memory base 3/4] RUN apt-get update && apt-get install -y --no-install-recommends     curl     postgresql-client     ca-certificates     && rm -rf /var/lib/apt/lists/*
#11 5.606 Preparing to unpack .../11-libgssapi-krb5-2_1.21.3-5_amd64.deb ...
#11 5.609 Unpacking libgssapi-krb5-2:amd64 (1.21.3-5) ...
#11 5.672 Selecting previously unselected package libunistring5:amd64.
#11 5.674 Preparing to unpack .../12-libunistring5_1.3-2_amd64.deb ...
#11 5.680 Unpacking libunistring5:amd64 (1.3-2) ...
#11 5.766 Selecting previously unselected package libidn2-0:amd64.
#11 ...

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 1.245 Requirement already satisfied: pip in /usr/local/lib/python3.12/site-packages (25.0.1)
#14 1.334 Collecting pip
#14 1.374   Downloading pip-26.0.1-py3-none-any.whl.metadata (4.7 kB)
#14 1.516 Collecting setuptools
#14 1.526   Downloading setuptools-80.10.2-py3-none-any.whl.metadata (6.6 kB)
#14 1.584 Collecting wheel
#14 1.594   Downloading wheel-0.46.3-py3-none-any.whl.metadata (2.4 kB)
#14 1.637 Collecting packaging>=24.0 (from wheel)
#14 1.648   Downloading packaging-26.0-py3-none-any.whl.metadata (3.3 kB)
#14 1.668 Downloading pip-26.0.1-py3-none-any.whl (1.8 MB)
#14 1.723    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 51.0 MB/s eta 0:00:00
#14 1.735 Downloading setuptools-80.10.2-py3-none-any.whl (1.1 MB)
#14 1.756    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 52.7 MB/s eta 0:00:00
#14 1.766 Downloading wheel-0.46.3-py3-none-any.whl (30 kB)
#14 1.784 Downloading packaging-26.0-py3-none-any.whl (74 kB)
#14 1.841 Installing collected packages: setuptools, pip, packaging, wheel
#14 2.405   Attempting uninstall: pip
#14 2.410     Found existing installation: pip 25.0.1
#14 2.473     Uninstalling pip-25.0.1:
#14 ...

#11 [l9-mcp-memory base 3/4] RUN apt-get update && apt-get install -y --no-install-recommends     curl     postgresql-client     ca-certificates     && rm -rf /var/lib/apt/lists/*
#11 5.768 Preparing to unpack .../13-libidn2-0_2.3.8-2_amd64.deb ...
#11 5.771 Unpacking libidn2-0:amd64 (2.3.8-2) ...
#11 5.818 Selecting previously unselected package libsasl2-modules-db:amd64.
#11 5.821 Preparing to unpack .../14-libsasl2-modules-db_2.1.28+dfsg1-9_amd64.deb ...
#11 5.824 Unpacking libsasl2-modules-db:amd64 (2.1.28+dfsg1-9) ...
#11 5.861 Selecting previously unselected package libsasl2-2:amd64.
#11 5.863 Preparing to unpack .../15-libsasl2-2_2.1.28+dfsg1-9_amd64.deb ...
#11 5.866 Unpacking libsasl2-2:amd64 (2.1.28+dfsg1-9) ...
#11 5.908 Selecting previously unselected package libldap2:amd64.
#11 5.910 Preparing to unpack .../16-libldap2_2.6.10+dfsg-1_amd64.deb ...
#11 5.913 Unpacking libldap2:amd64 (2.6.10+dfsg-1) ...
#11 5.972 Selecting previously unselected package libnghttp2-14:amd64.
#11 5.974 Preparing to unpack .../17-libnghttp2-14_1.64.0-1.1_amd64.deb ...
#11 5.977 Unpacking libnghttp2-14:amd64 (1.64.0-1.1) ...
#11 6.024 Selecting previously unselected package libnghttp3-9:amd64.
#11 6.026 Preparing to unpack .../18-libnghttp3-9_1.8.0-1_amd64.deb ...
#11 6.030 Unpacking libnghttp3-9:amd64 (1.8.0-1) ...
#11 6.076 Selecting previously unselected package libpsl5t64:amd64.
#11 6.078 Preparing to unpack .../19-libpsl5t64_0.21.2-1.1+b1_amd64.deb ...
#11 6.081 Unpacking libpsl5t64:amd64 (0.21.2-1.1+b1) ...
#11 6.124 Selecting previously unselected package libp11-kit0:amd64.
#11 6.127 Preparing to unpack .../20-libp11-kit0_0.25.5-3_amd64.deb ...
#11 6.130 Unpacking libp11-kit0:amd64 (0.25.5-3) ...
#11 6.202 Selecting previously unselected package libtasn1-6:amd64.
#11 6.204 Preparing to unpack .../21-libtasn1-6_4.20.0-2_amd64.deb ...
#11 6.207 Unpacking libtasn1-6:amd64 (4.20.0-2) ...
#11 6.251 Selecting previously unselected package libgnutls30t64:amd64.
#11 6.253 Preparing to unpack .../22-libgnutls30t64_3.8.9-3+deb13u1_amd64.deb ...
#11 6.256 Unpacking libgnutls30t64:amd64 (3.8.9-3+deb13u1) ...
#11 6.366 Selecting previously unselected package librtmp1:amd64.
#11 6.367 Preparing to unpack .../23-librtmp1_2.4+20151223.gitfa8646d.1-2+b5_amd64.deb ...
#11 6.370 Unpacking librtmp1:amd64 (2.4+20151223.gitfa8646d.1-2+b5) ...
#11 6.406 Selecting previously unselected package libssh2-1t64:amd64.
#11 6.408 Preparing to unpack .../24-libssh2-1t64_1.11.1-1_amd64.deb ...
#11 6.411 Unpacking libssh2-1t64:amd64 (1.11.1-1) ...
#11 6.464 Selecting previously unselected package libcurl4t64:amd64.
#11 6.466 Preparing to unpack .../25-libcurl4t64_8.14.1-2+deb13u2_amd64.deb ...
#11 6.469 Unpacking libcurl4t64:amd64 (8.14.1-2+deb13u2) ...
#11 6.537 Selecting previously unselected package curl.
#11 6.539 Preparing to unpack .../26-curl_8.14.1-2+deb13u2_amd64.deb ...
#11 6.542 Unpacking curl (8.14.1-2+deb13u2) ...
#11 6.600 Selecting previously unselected package libpq5:amd64.
#11 6.602 Preparing to unpack .../27-libpq5_17.7-0+deb13u1_amd64.deb ...
#11 6.605 Unpacking libpq5:amd64 (17.7-0+deb13u1) ...
#11 6.668 Selecting previously unselected package postgresql-client-common.
#11 6.670 Preparing to unpack .../28-postgresql-client-common_278_all.deb ...
#11 6.684 Unpacking postgresql-client-common (278) ...
#11 6.732 Selecting previously unselected package postgresql-client-17.
#11 6.734 Preparing to unpack .../29-postgresql-client-17_17.7-0+deb13u1_amd64.deb ...
#11 6.737 Unpacking postgresql-client-17 (17.7-0+deb13u1) ...
#11 6.897 Selecting previously unselected package postgresql-client.
#11 6.899 Preparing to unpack .../30-postgresql-client_17+278_all.deb ...
#11 6.901 Unpacking postgresql-client (17+278) ...
#11 6.945 Setting up libkeyutils1:amd64 (1.6.3-6) ...
#11 6.954 Setting up libgdbm-compat4t64:amd64 (1.24-2) ...
#11 6.962 Setting up libbrotli1:amd64 (1.1.0-2+b7) ...
#11 6.971 Setting up libnghttp2-14:amd64 (1.64.0-1.1) ...
#11 6.979 Setting up libcom-err2:amd64 (1.47.2-3+b7) ...
#11 6.987 Setting up libkrb5support0:amd64 (1.21.3-5) ...
#11 6.996 Setting up libsasl2-modules-db:amd64 (2.1.28+dfsg1-9) ...
#11 7.004 Setting up libp11-kit0:amd64 (0.25.5-3) ...
#11 7.012 Setting up libunistring5:amd64 (1.3-2) ...
#11 7.020 Setting up libk5crypto3:amd64 (1.21.3-5) ...
#11 7.029 Setting up libsasl2-2:amd64 (2.1.28+dfsg1-9) ...
#11 7.037 Setting up libnghttp3-9:amd64 (1.8.0-1) ...
#11 7.046 Setting up perl-modules-5.40 (5.40.1-6) ...
#11 7.054 Setting up sensible-utils (0.0.25) ...
#11 7.062 Setting up libtasn1-6:amd64 (4.20.0-2) ...
#11 7.071 Setting up libkrb5-3:amd64 (1.21.3-5) ...
#11 7.079 Setting up libssh2-1t64:amd64 (1.11.1-1) ...
#11 7.086 Setting up libldap2:amd64 (2.6.10+dfsg-1) ...
#11 7.096 Setting up libidn2-0:amd64 (2.3.8-2) ...
#11 7.103 Setting up libperl5.40:amd64 (5.40.1-6) ...
#11 7.116 Setting up perl (5.40.1-6) ...
#11 7.135 Setting up libgssapi-krb5-2:amd64 (1.21.3-5) ...
#11 7.146 Setting up libgnutls30t64:amd64 (3.8.9-3+deb13u1) ...
#11 7.155 Setting up postgresql-client-common (278) ...
#11 7.176 Setting up libpsl5t64:amd64 (0.21.2-1.1+b1) ...
#11 7.184 Setting up libpq5:amd64 (17.7-0+deb13u1) ...
#11 7.194 Setting up librtmp1:amd64 (2.4+20151223.gitfa8646d.1-2+b5) ...
#11 7.202 Setting up libcurl4t64:amd64 (8.14.1-2+deb13u2) ...
#11 7.210 Setting up postgresql-client-17 (17.7-0+deb13u1) ...
#11 8.062 update-alternatives: using /usr/share/postgresql/17/man/man1/psql.1.gz to provide /usr/share/man/man1/psql.1.gz (psql.1.gz) in auto mode
#11 8.152 Setting up curl (8.14.1-2+deb13u2) ...
#11 8.162 Setting up postgresql-client (17+278) ...
#11 8.170 Processing triggers for libc-bin (2.41-12+deb13u1) ...
#11 DONE 8.3s

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 2.688       Successfully uninstalled pip-25.0.1
#14 ...

#15 [l9-mcp-memory base 4/4] RUN useradd -m -u 1000 l9user &&     chown -R l9user:l9user /app
#15 DONE 0.4s

#16 [l9-mcp-memory production  1/10] COPY requirements-mcp-memory.txt /app/
#16 DONE 0.0s

#17 [l9-mcp-memory production  2/10] RUN pip install --no-cache-dir -r requirements-mcp-memory.txt &&     pip cache purge
#17 1.284 Collecting mcp>=1.0.0 (from -r requirements-mcp-memory.txt (line 6))
#17 1.318   Downloading mcp-1.26.0-py3-none-any.whl.metadata (89 kB)
#17 1.368 Collecting pydantic-settings>=2.0.0 (from -r requirements-mcp-memory.txt (line 7))
#17 1.378   Downloading pydantic_settings-2.12.0-py3-none-any.whl.metadata (3.4 kB)
#17 1.461 Collecting fastapi>=0.115.0 (from -r requirements-mcp-memory.txt (line 10))
#17 1.470   Downloading fastapi-0.128.2-py3-none-any.whl.metadata (30 kB)
#17 1.524 Collecting uvicorn>=0.30.0 (from uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 1.533   Downloading uvicorn-0.40.0-py3-none-any.whl.metadata (6.7 kB)
#17 1.567 Collecting httpx>=0.27.0 (from -r requirements-mcp-memory.txt (line 12))
#17 1.578   Downloading httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
#17 1.644 Collecting asyncpg>=0.29.0 (from -r requirements-mcp-memory.txt (line 15))
#17 1.656   Downloading asyncpg-0.31.0-cp312-cp312-manylinux_2_28_x86_64.whl.metadata (4.4 kB)
#17 1.689 Collecting psycopg>=3.1.0 (from psycopg[binary]>=3.1.0->-r requirements-mcp-memory.txt (line 16))
#17 1.700   Downloading psycopg-3.3.2-py3-none-any.whl.metadata (4.3 kB)
#17 1.726 Collecting pgvector>=0.2.5 (from -r requirements-mcp-memory.txt (line 17))
#17 1.736   Downloading pgvector-0.4.2-py3-none-any.whl.metadata (19 kB)
#17 1.833 Collecting openai>=1.0.0 (from -r requirements-mcp-memory.txt (line 20))
#17 1.842   Downloading openai-2.17.0-py3-none-any.whl.metadata (29 kB)
#17 1.868 Collecting tenacity>=8.2.0 (from -r requirements-mcp-memory.txt (line 21))
#17 1.878   Downloading tenacity-9.1.3-py3-none-any.whl.metadata (1.2 kB)
#17 1.953 Collecting langgraph>=0.0.40 (from -r requirements-mcp-memory.txt (line 22))
#17 1.965   Downloading langgraph-1.0.7-py3-none-any.whl.metadata (7.4 kB)
#17 1.991 Collecting structlog>=24.1.0 (from -r requirements-mcp-memory.txt (line 25))
#17 2.002   Downloading structlog-25.5.0-py3-none-any.whl.metadata (9.5 kB)
#17 2.027 Collecting prometheus_client>=0.19.0 (from -r requirements-mcp-memory.txt (line 28))
#17 2.038   Downloading prometheus_client-0.24.1-py3-none-any.whl.metadata (2.1 kB)
#17 2.064 Collecting python-dotenv>=1.0.0 (from -r requirements-mcp-memory.txt (line 31))
#17 2.074   Downloading python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
#17 2.132 Collecting pyyaml>=6.0.1 (from -r requirements-mcp-memory.txt (line 32))
#17 2.142   Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
#17 2.161 Collecting aiofiles>=23.2.0 (from -r requirements-mcp-memory.txt (line 33))
#17 2.170   Downloading aiofiles-25.1.0-py3-none-any.whl.metadata (6.3 kB)
#17 2.333 Collecting numpy>=1.24.0 (from -r requirements-mcp-memory.txt (line 34))
#17 2.342   Downloading numpy-2.4.2-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl.metadata (6.6 kB)
#17 2.385 Collecting tiktoken>=0.5.0 (from -r requirements-mcp-memory.txt (line 35))
#17 2.395   Downloading tiktoken-0.12.0-cp312-cp312-manylinux_2_28_x86_64.whl.metadata (6.7 kB)
#17 2.440 Collecting redis>=4.0.0 (from -r requirements-mcp-memory.txt (line 38))
#17 2.449   Downloading redis-7.1.0-py3-none-any.whl.metadata (12 kB)
#17 2.481 Collecting neo4j>=5.0.0 (from -r requirements-mcp-memory.txt (line 39))
#17 2.492   Downloading neo4j-6.1.0-py3-none-any.whl.metadata (5.3 kB)
#17 2.549 Collecting pytest>=8.0.0 (from -r requirements-mcp-memory.txt (line 42))
#17 2.558   Downloading pytest-9.0.2-py3-none-any.whl.metadata (7.6 kB)
#17 2.592 Collecting pytest-asyncio>=0.23.0 (from -r requirements-mcp-memory.txt (line 43))
#17 2.603   Downloading pytest_asyncio-1.3.0-py3-none-any.whl.metadata (4.1 kB)
#17 2.636 Collecting anyio>=4.5 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.646   Downloading anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
#17 2.664 Collecting httpx-sse>=0.4 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.675   Downloading httpx_sse-0.4.3-py3-none-any.whl.metadata (9.7 kB)
#17 2.724 Collecting jsonschema>=4.20.0 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.734   Downloading jsonschema-4.26.0-py3-none-any.whl.metadata (7.6 kB)
#17 2.860 Collecting pydantic<3.0.0,>=2.11.0 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.869   Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
#17 2.905 Collecting pyjwt>=2.10.1 (from pyjwt[crypto]>=2.10.1->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.915   Downloading pyjwt-2.11.0-py3-none-any.whl.metadata (4.0 kB)
#17 2.939 Collecting python-multipart>=0.0.9 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.949   Downloading python_multipart-0.0.22-py3-none-any.whl.metadata (1.8 kB)
#17 2.978 Collecting sse-starlette>=1.6.1 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 2.988   Downloading sse_starlette-3.2.0-py3-none-any.whl.metadata (12 kB)
#17 3.041 Collecting starlette>=0.27 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 3.051   Downloading starlette-0.52.1-py3-none-any.whl.metadata (6.3 kB)
#17 3.080 Collecting typing-extensions>=4.9.0 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 3.090   Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
#17 3.107 Collecting typing-inspection>=0.4.1 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 3.117   Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
#17 3.185 Collecting starlette>=0.27 (from mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 3.194   Downloading starlette-0.50.0-py3-none-any.whl.metadata (6.3 kB)
#17 3.217 Collecting annotated-doc>=0.0.2 (from fastapi>=0.115.0->-r requirements-mcp-memory.txt (line 10))
#17 3.227   Downloading annotated_doc-0.0.4-py3-none-any.whl.metadata (6.6 kB)
#17 3.259 Collecting click>=7.0 (from uvicorn>=0.30.0->uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 3.268   Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
#17 3.286 Collecting h11>=0.8 (from uvicorn>=0.30.0->uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 3.296   Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
#17 3.328 Collecting certifi (from httpx>=0.27.0->-r requirements-mcp-memory.txt (line 12))
#17 3.338   Downloading certifi-2026.1.4-py3-none-any.whl.metadata (2.5 kB)
#17 3.369 Collecting httpcore==1.* (from httpx>=0.27.0->-r requirements-mcp-memory.txt (line 12))
#17 3.378   Downloading httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
#17 3.402 Collecting idna (from httpx>=0.27.0->-r requirements-mcp-memory.txt (line 12))
#17 3.412   Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
#17 3.435 Collecting distro<2,>=1.7.0 (from openai>=1.0.0->-r requirements-mcp-memory.txt (line 20))
#17 3.443   Downloading distro-1.9.0-py3-none-any.whl.metadata (6.8 kB)
#17 3.521 Collecting jiter<1,>=0.10.0 (from openai>=1.0.0->-r requirements-mcp-memory.txt (line 20))
#17 3.531   Downloading jiter-0.13.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (5.2 kB)
#17 3.552 Collecting sniffio (from openai>=1.0.0->-r requirements-mcp-memory.txt (line 20))
#17 3.560   Downloading sniffio-1.3.1-py3-none-any.whl.metadata (3.9 kB)
#17 3.598 Collecting tqdm>4 (from openai>=1.0.0->-r requirements-mcp-memory.txt (line 20))
#17 3.607   Downloading tqdm-4.67.3-py3-none-any.whl.metadata (57 kB)
#17 3.689 Collecting langchain-core>=0.1 (from langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 3.698   Downloading langchain_core-1.2.9-py3-none-any.whl.metadata (4.4 kB)
#17 3.714 Collecting langgraph-checkpoint<5.0.0,>=2.1.0 (from langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 3.724   Downloading langgraph_checkpoint-4.0.0-py3-none-any.whl.metadata (4.9 kB)
#17 3.746 Collecting langgraph-prebuilt<1.1.0,>=1.0.7 (from langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 3.760   Downloading langgraph_prebuilt-1.0.7-py3-none-any.whl.metadata (5.2 kB)
#17 3.800 Collecting langgraph-sdk<0.4.0,>=0.3.0 (from langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 3.810   Downloading langgraph_sdk-0.3.4-py3-none-any.whl.metadata (1.6 kB)
#17 3.921 Collecting xxhash>=3.5.0 (from langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 3.931   Downloading xxhash-3.6.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (13 kB)
#17 4.194 Collecting regex>=2022.1.18 (from tiktoken>=0.5.0->-r requirements-mcp-memory.txt (line 35))
#17 4.203   Downloading regex-2026.1.15-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (40 kB)
#17 4.226 Collecting requests>=2.26.0 (from tiktoken>=0.5.0->-r requirements-mcp-memory.txt (line 35))
#17 4.234   Downloading requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
#17 4.265 Collecting pytz (from neo4j>=5.0.0->-r requirements-mcp-memory.txt (line 39))
#17 4.274   Downloading pytz-2025.2-py2.py3-none-any.whl.metadata (22 kB)
#17 4.287 Collecting iniconfig>=1.0.1 (from pytest>=8.0.0->-r requirements-mcp-memory.txt (line 42))
#17 4.295   Downloading iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
#17 4.316 Collecting packaging>=22 (from pytest>=8.0.0->-r requirements-mcp-memory.txt (line 42))
#17 4.326   Downloading packaging-26.0-py3-none-any.whl.metadata (3.3 kB)
#17 4.346 Collecting pluggy<2,>=1.5 (from pytest>=8.0.0->-r requirements-mcp-memory.txt (line 42))
#17 4.355   Downloading pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
#17 4.390 Collecting pygments>=2.7.2 (from pytest>=8.0.0->-r requirements-mcp-memory.txt (line 42))
#17 4.400   Downloading pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
#17 4.590 Collecting psycopg-binary==3.3.2 (from psycopg[binary]>=3.1.0->-r requirements-mcp-memory.txt (line 16))
#17 4.599   Downloading psycopg_binary-3.3.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.7 kB)
#17 4.635 Collecting httptools>=0.6.3 (from uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 4.645   Downloading httptools-0.7.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (3.5 kB)
#17 4.699 Collecting uvloop>=0.15.1 (from uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 4.708   Downloading uvloop-0.22.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (4.9 kB)
#17 4.785 Collecting watchfiles>=0.13 (from uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 4.795   Downloading watchfiles-1.1.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.9 kB)
#17 4.876 Collecting websockets>=10.4 (from uvicorn[standard]>=0.30.0->-r requirements-mcp-memory.txt (line 11))
#17 4.885   Downloading websockets-16.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (6.8 kB)
#17 4.927 Collecting attrs>=22.2.0 (from jsonschema>=4.20.0->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 4.936   Downloading attrs-25.4.0-py3-none-any.whl.metadata (10 kB)
#17 4.955 Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=4.20.0->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 4.965   Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
#17 5.005 Collecting referencing>=0.28.4 (from jsonschema>=4.20.0->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 5.014   Downloading referencing-0.37.0-py3-none-any.whl.metadata (2.8 kB)
#17 5.213 Collecting rpds-py>=0.25.0 (from jsonschema>=4.20.0->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 5.222   Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.1 kB)
#17 5.242 Collecting jsonpatch<2.0.0,>=1.33.0 (from langchain-core>=0.1->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 5.252   Downloading jsonpatch-1.33-py2.py3-none-any.whl.metadata (3.0 kB)
#17 5.333 Collecting langsmith<1.0.0,>=0.3.45 (from langchain-core>=0.1->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 5.342   Downloading langsmith-0.6.9-py3-none-any.whl.metadata (15 kB)
#17 5.449 Collecting uuid-utils<1.0,>=0.12.0 (from langchain-core>=0.1->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 5.458   Downloading uuid_utils-0.14.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.9 kB)
#17 5.520 Collecting ormsgpack>=1.12.0 (from langgraph-checkpoint<5.0.0,>=2.1.0->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 5.529   Downloading ormsgpack-1.12.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (3.2 kB)
#17 5.710 Collecting orjson>=3.10.1 (from langgraph-sdk<0.4.0,>=0.3.0->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 5.719   Downloading orjson-3.11.7-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (41 kB)
#17 5.736 Collecting annotated-types>=0.6.0 (from pydantic<3.0.0,>=2.11.0->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 5.744   Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
#17 6.219 Collecting pydantic-core==2.41.5 (from pydantic<3.0.0,>=2.11.0->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 6.229   Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (7.3 kB)
#17 6.417 Collecting cryptography>=3.4.0 (from pyjwt[crypto]>=2.10.1->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 6.427   Downloading cryptography-46.0.4-cp311-abi3-manylinux_2_34_x86_64.whl.metadata (5.7 kB)
#17 6.535 Collecting charset_normalizer<4,>=2 (from requests>=2.26.0->tiktoken>=0.5.0->-r requirements-mcp-memory.txt (line 35))
#17 6.545   Downloading charset_normalizer-3.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (37 kB)
#17 6.585 Collecting urllib3<3,>=1.21.1 (from requests>=2.26.0->tiktoken>=0.5.0->-r requirements-mcp-memory.txt (line 35))
#17 6.595   Downloading urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
#17 6.754 Collecting cffi>=2.0.0 (from cryptography>=3.4.0->pyjwt[crypto]>=2.10.1->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 6.763   Downloading cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.6 kB)
#17 6.781 Collecting jsonpointer>=1.9 (from jsonpatch<2.0.0,>=1.33.0->langchain-core>=0.1->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 6.789   Downloading jsonpointer-3.0.0-py2.py3-none-any.whl.metadata (2.3 kB)
#17 6.832 Collecting requests-toolbelt>=1.0.0 (from langsmith<1.0.0,>=0.3.45->langchain-core>=0.1->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 6.840   Downloading requests_toolbelt-1.0.0-py2.py3-none-any.whl.metadata (14 kB)
#17 6.903 Collecting zstandard>=0.23.0 (from langsmith<1.0.0,>=0.3.45->langchain-core>=0.1->langgraph>=0.0.40->-r requirements-mcp-memory.txt (line 22))
#17 6.912   Downloading zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (3.3 kB)
#17 6.951 Collecting pycparser (from cffi>=2.0.0->cryptography>=3.4.0->pyjwt[crypto]>=2.10.1->mcp>=1.0.0->-r requirements-mcp-memory.txt (line 6))
#17 6.959   Downloading pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
#17 6.991 Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
#17 7.007 Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
#17 7.016 Downloading fastapi-0.128.2-py3-none-any.whl (104 kB)
#17 7.026 Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
#17 7.035 Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
#17 7.044 Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
#17 7.058 Downloading asyncpg-0.31.0-cp312-cp312-manylinux_2_28_x86_64.whl (3.5 MB)
#17 7.086    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.5/3.5 MB 145.1 MB/s eta 0:00:00
#17 7.097 Downloading psycopg-3.3.2-py3-none-any.whl (212 kB)
#17 7.107 Downloading pgvector-0.4.2-py3-none-any.whl (27 kB)
#17 7.118 Downloading openai-2.17.0-py3-none-any.whl (1.1 MB)
#17 7.125    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 298.5 MB/s eta 0:00:00
#17 7.135 Downloading tenacity-9.1.3-py3-none-any.whl (28 kB)
#17 7.145 Downloading langgraph-1.0.7-py3-none-any.whl (157 kB)
#17 7.157 Downloading structlog-25.5.0-py3-none-any.whl (72 kB)
#17 7.167 Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
#17 7.177 Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
#17 7.187 Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (807 kB)
#17 7.193    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 807.9/807.9 kB 338.1 MB/s eta 0:00:00
#17 7.203 Downloading aiofiles-25.1.0-py3-none-any.whl (14 kB)
#17 7.213 Downloading numpy-2.4.2-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (16.6 MB)
#17 7.287    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 16.6/16.6 MB 236.6 MB/s eta 0:00:00
#17 7.300 Downloading tiktoken-0.12.0-cp312-cp312-manylinux_2_28_x86_64.whl (1.2 MB)
#17 7.309    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 228.9 MB/s eta 0:00:00
#17 7.320 Downloading redis-7.1.0-py3-none-any.whl (354 kB)
#17 7.333 Downloading neo4j-6.1.0-py3-none-any.whl (325 kB)
#17 7.346 Downloading pytest-9.0.2-py3-none-any.whl (374 kB)
#17 7.358 Downloading pytest_asyncio-1.3.0-py3-none-any.whl (15 kB)
#17 7.369 Downloading psycopg_binary-3.3.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (5.1 MB)
#17 7.391    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.1/5.1 MB 276.9 MB/s eta 0:00:00
#17 7.401 Downloading annotated_doc-0.0.4-py3-none-any.whl (5.3 kB)
#17 7.412 Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
#17 7.423 Downloading click-8.3.1-py3-none-any.whl (108 kB)
#17 7.433 Downloading distro-1.9.0-py3-none-any.whl (20 kB)
#17 7.443 Downloading h11-0.16.0-py3-none-any.whl (37 kB)
#17 7.455 Downloading httptools-0.7.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (517 kB)
#17 7.467 Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
#17 7.478 Downloading idna-3.11-py3-none-any.whl (71 kB)
#17 7.488 Downloading iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
#17 7.501 Downloading jiter-0.13.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (360 kB)
#17 7.513 Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
#17 7.524 Downloading langchain_core-1.2.9-py3-none-any.whl (496 kB)
#17 7.541 Downloading langgraph_checkpoint-4.0.0-py3-none-any.whl (46 kB)
#17 7.552 Downloading langgraph_prebuilt-1.0.7-py3-none-any.whl (35 kB)
#17 7.563 Downloading langgraph_sdk-0.3.4-py3-none-any.whl (67 kB)
#17 7.573 Downloading packaging-26.0-py3-none-any.whl (74 kB)
#17 7.584 Downloading pluggy-1.6.0-py3-none-any.whl (20 kB)
#17 7.594 Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
#17 7.606 Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.1 MB)
#17 7.615    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 319.1 MB/s eta 0:00:00
#17 7.625 Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
#17 7.632    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 326.7 MB/s eta 0:00:00
#17 7.642 Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
#17 7.652 Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
#17 7.663 Downloading regex-2026.1.15-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (803 kB)
#17 7.669    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 803.6/803.6 kB 295.0 MB/s eta 0:00:00
#17 7.680 Downloading requests-2.32.5-py3-none-any.whl (64 kB)
#17 7.690 Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
#17 7.700 Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
#17 7.710 Downloading starlette-0.50.0-py3-none-any.whl (74 kB)
#17 7.720 Downloading tqdm-4.67.3-py3-none-any.whl (78 kB)
#17 7.730 Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
#17 7.740 Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
#17 7.756 Downloading uvloop-0.22.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.4 MB)
#17 7.775    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.4/4.4 MB 278.3 MB/s eta 0:00:00
#17 7.786 Downloading watchfiles-1.1.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (456 kB)
#17 7.799 Downloading websockets-16.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (184 kB)
#17 7.810 Downloading xxhash-3.6.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (193 kB)
#17 7.821 Downloading pytz-2025.2-py2.py3-none-any.whl (509 kB)
#17 7.833 Downloading sniffio-1.3.1-py3-none-any.whl (10 kB)
#17 7.843 Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
#17 7.853 Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
#17 7.864 Downloading charset_normalizer-3.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (153 kB)
#17 7.874 Downloading cryptography-46.0.4-cp311-abi3-manylinux_2_34_x86_64.whl (4.5 MB)
#17 7.894    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.5/4.5 MB 313.7 MB/s eta 0:00:00
#17 7.904 Downloading jsonpatch-1.33-py2.py3-none-any.whl (12 kB)
#17 7.914 Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
#17 7.925 Downloading langsmith-0.6.9-py3-none-any.whl (319 kB)
#17 7.937 Downloading orjson-3.11.7-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (133 kB)
#17 7.949 Downloading ormsgpack-1.12.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (212 kB)
#17 7.960 Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
#17 7.970 Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (394 kB)
#17 7.982 Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
#17 7.994 Downloading uuid_utils-0.14.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (341 kB)
#17 8.006 Downloading cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (219 kB)
#17 8.016 Downloading jsonpointer-3.0.0-py2.py3-none-any.whl (7.6 kB)
#17 8.026 Downloading requests_toolbelt-1.0.0-py2.py3-none-any.whl (54 kB)
#17 8.037 Downloading zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (5.5 MB)
#17 8.071    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.5/5.5 MB 184.0 MB/s eta 0:00:00
#17 8.081 Downloading pycparser-3.0-py3-none-any.whl (48 kB)
#17 8.365 Installing collected packages: pytz, zstandard, xxhash, websockets, uvloop, uuid-utils, urllib3, typing-extensions, tqdm, tenacity, structlog, sniffio, rpds-py, regex, redis, pyyaml, python-multipart, python-dotenv, pyjwt, pygments, pycparser, psycopg-binary, prometheus_client, pluggy, packaging, ormsgpack, orjson, numpy, neo4j, jsonpointer, jiter, iniconfig, idna, httpx-sse, httptools, h11, distro, click, charset_normalizer, certifi, attrs, asyncpg, annotated-types, annotated-doc, aiofiles, uvicorn, typing-inspection, requests, referencing, pytest, pydantic-core, psycopg, pgvector, jsonpatch, httpcore, cffi, anyio, watchfiles, tiktoken, starlette, requests-toolbelt, pytest-asyncio, pydantic, jsonschema-specifications, httpx, cryptography, sse-starlette, pydantic-settings, openai, langsmith, langgraph-sdk, jsonschema, fastapi, mcp, langchain-core, langgraph-checkpoint, langgraph-prebuilt, langgraph
#17 ...

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 3.523 Successfully installed packaging-26.0 pip-26.0.1 setuptools-80.10.2 wheel-0.46.3
#14 3.524 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#14 4.353 Looking in indexes: https://download.pytorch.org/whl/cpu
#14 5.296 Collecting torch
#14 5.301   Downloading https://download.pytorch.org/whl/cpu/torch-2.10.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl.metadata (29 kB)
#14 5.805 Collecting filelock (from torch)
#14 5.867   Downloading filelock-3.20.0-py3-none-any.whl.metadata (2.1 kB)
#14 6.258 Collecting typing-extensions>=4.10.0 (from torch)
#14 6.263   Downloading https://download.pytorch.org/whl/typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
#14 6.267 Requirement already satisfied: setuptools in /usr/local/lib/python3.12/site-packages (from torch) (80.10.2)
#14 6.777 Collecting sympy>=1.13.3 (from torch)
#14 6.787   Downloading sympy-1.14.0-py3-none-any.whl.metadata (12 kB)
#14 7.412 Collecting networkx>=2.5.1 (from torch)
#14 7.422   Downloading networkx-3.6.1-py3-none-any.whl.metadata (6.8 kB)
#14 7.824 Collecting jinja2 (from torch)
#14 7.829   Downloading https://download.pytorch.org/whl/jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
#14 8.342 Collecting fsspec>=0.8.5 (from torch)
#14 8.353   Downloading fsspec-2025.12.0-py3-none-any.whl.metadata (10 kB)
#14 8.773 Collecting mpmath<1.4,>=1.1.0 (from sympy>=1.13.3->torch)
#14 8.784   Downloading mpmath-1.3.0-py3-none-any.whl.metadata (8.6 kB)
#14 9.184 Collecting MarkupSafe>=2.0 (from jinja2->torch)
#14 9.192   Downloading https://download.pytorch.org/whl/MarkupSafe-2.1.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (28 kB)
#14 9.215 Downloading https://download.pytorch.org/whl/cpu/torch-2.10.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl (188.9 MB)
#14 9.904    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 188.9/188.9 MB 276.4 MB/s  0:00:00
#14 9.915 Downloading fsspec-2025.12.0-py3-none-any.whl (201 kB)
#14 9.942 Downloading networkx-3.6.1-py3-none-any.whl (2.1 MB)
#14 9.966    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 121.2 MB/s  0:00:00
#14 9.977 Downloading sympy-1.14.0-py3-none-any.whl (6.3 MB)
#14 10.00    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.3/6.3 MB 306.9 MB/s  0:00:00
#14 10.01 Downloading mpmath-1.3.0-py3-none-any.whl (536 kB)
#14 10.01    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 536.2/536.2 kB 164.2 MB/s  0:00:00
#14 10.02 Downloading https://download.pytorch.org/whl/typing_extensions-4.15.0-py3-none-any.whl (44 kB)
#14 10.03 Downloading filelock-3.20.0-py3-none-any.whl (16 kB)
#14 10.03 Downloading https://download.pytorch.org/whl/jinja2-3.1.6-py3-none-any.whl (134 kB)
#14 10.32 Installing collected packages: mpmath, typing-extensions, sympy, networkx, MarkupSafe, fsspec, filelock, jinja2, torch
#14 ...

#17 [l9-mcp-memory production  2/10] RUN pip install --no-cache-dir -r requirements-mcp-memory.txt &&     pip cache purge
#17 15.20 Successfully installed aiofiles-25.1.0 annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.12.1 asyncpg-0.31.0 attrs-25.4.0 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cryptography-46.0.4 distro-1.9.0 fastapi-0.128.2 h11-0.16.0 httpcore-1.0.9 httptools-0.7.1 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 iniconfig-2.3.0 jiter-0.13.0 jsonpatch-1.33 jsonpointer-3.0.0 jsonschema-4.26.0 jsonschema-specifications-2025.9.1 langchain-core-1.2.9 langgraph-1.0.7 langgraph-checkpoint-4.0.0 langgraph-prebuilt-1.0.7 langgraph-sdk-0.3.4 langsmith-0.6.9 mcp-1.26.0 neo4j-6.1.0 numpy-2.4.2 openai-2.17.0 orjson-3.11.7 ormsgpack-1.12.2 packaging-26.0 pgvector-0.4.2 pluggy-1.6.0 prometheus_client-0.24.1 psycopg-3.3.2 psycopg-binary-3.3.2 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pygments-2.19.2 pyjwt-2.11.0 pytest-9.0.2 pytest-asyncio-1.3.0 python-dotenv-1.2.1 python-multipart-0.0.22 pytz-2025.2 pyyaml-6.0.3 redis-7.1.0 referencing-0.37.0 regex-2026.1.15 requests-2.32.5 requests-toolbelt-1.0.0 rpds-py-0.30.0 sniffio-1.3.1 sse-starlette-3.2.0 starlette-0.50.0 structlog-25.5.0 tenacity-9.1.3 tiktoken-0.12.0 tqdm-4.67.3 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uuid-utils-0.14.0 uvicorn-0.40.0 uvloop-0.22.1 watchfiles-1.1.1 websockets-16.0 xxhash-3.6.0 zstandard-0.25.0
#17 15.20 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#17 15.32 
#17 15.32 [notice] A new release of pip is available: 25.0.1 -> 26.0.1
#17 15.32 [notice] To update, run: pip install --upgrade pip
#17 16.31 WARNING: No matching packages
#17 16.31 Files removed: 0 (0 bytes)
#17 DONE 16.7s

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 ...

#18 [l9-mcp-memory production  3/10] COPY --chown=l9user:l9user mcp_memory/ /app/mcp_memory/
#18 DONE 0.1s

#19 [l9-mcp-memory production  4/10] COPY --chown=l9user:l9user core/ /app/core/
#19 DONE 0.2s

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 ...

#20 [l9-mcp-memory production  5/10] COPY --chown=l9user:l9user memory/ /app/memory/
#20 DONE 0.1s

#21 [l9-mcp-memory production  6/10] COPY --chown=l9user:l9user config/ /app/config/
#21 DONE 0.0s

#22 [l9-mcp-memory production  7/10] COPY --chown=l9user:l9user telemetry/ /app/telemetry/
#22 DONE 0.0s

#23 [l9-mcp-memory production  8/10] COPY --chown=l9user:l9user private/ /app/private/
#23 DONE 0.0s

#24 [l9-mcp-memory production  9/10] COPY --chown=l9user:l9user migrations/ /app/migrations/
#24 DONE 0.0s

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 ...

#25 [l9-mcp-memory production 10/10] RUN test -f /app/mcp_memory/src/main.py || (echo "ERROR: mcp_memory/src/main.py not found" && exit 1) &&     test -f /app/requirements-mcp-memory.txt || (echo "ERROR: requirements-mcp-memory.txt not found" && exit 1)
#25 DONE 0.3s

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 ...

#26 [l9-mcp-memory] exporting to image
#26 exporting layers
#26 exporting layers 2.3s done
#26 writing image sha256:7d0c606496ae95ea2b9c39c84299ada6b1360036517373ae00e22d5c44c2a12b done
#26 naming to ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0 done
#26 DONE 2.3s

#27 [l9-mcp-memory] resolving provenance for metadata file
#27 DONE 0.0s

#14 [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu &&     pip install --no-cache-dir -r requirements-docker.txt &&     pip cache purge
#14 25.13 
#14 25.14 Successfully installed MarkupSafe-2.1.5 filelock-3.20.0 fsspec-2025.12.0 jinja2-3.1.6 mpmath-1.3.0 networkx-3.6.1 sympy-1.14.0 torch-2.10.0+cpu typing-extensions-4.15.0
#14 25.14 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#14 26.77 Collecting fastapi>=0.109.0 (from -r requirements-docker.txt (line 25))
#14 26.82   Downloading fastapi-0.128.2-py3-none-any.whl.metadata (30 kB)
#14 26.87 Collecting uvicorn>=0.27.0 (from uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 26.88   Downloading uvicorn-0.40.0-py3-none-any.whl.metadata (6.7 kB)
#14 27.00 Collecting pydantic>=2.5.0 (from -r requirements-docker.txt (line 27))
#14 27.01   Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
#14 27.03 Collecting python-dotenv>=1.0.0 (from -r requirements-docker.txt (line 28))
#14 27.04   Downloading python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
#14 27.08 Collecting pydantic-settings>=2.1.0 (from -r requirements-docker.txt (line 31))
#14 27.09   Downloading pydantic_settings-2.12.0-py3-none-any.whl.metadata (3.4 kB)
#14 27.12 Collecting psycopg>=3.1.14 (from psycopg[binary]>=3.1.14->-r requirements-docker.txt (line 34))
#14 27.13   Downloading psycopg-3.3.2-py3-none-any.whl.metadata (4.3 kB)
#14 27.34 Collecting sqlalchemy>=2.0.23 (from -r requirements-docker.txt (line 35))
#14 27.35   Downloading sqlalchemy-2.0.46-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (9.5 kB)
#14 27.40 Collecting asyncpg>=0.29.0 (from -r requirements-docker.txt (line 36))
#14 27.41   Downloading asyncpg-0.31.0-cp312-cp312-manylinux_2_28_x86_64.whl.metadata (4.4 kB)
#14 27.42 Collecting pgvector>=0.2.4 (from -r requirements-docker.txt (line 37))
#14 27.43   Downloading pgvector-0.4.2-py3-none-any.whl.metadata (19 kB)
#14 27.47 Collecting redis>=5.0.0 (from -r requirements-docker.txt (line 40))
#14 27.48   Downloading redis-7.1.0-py3-none-any.whl.metadata (12 kB)
#14 27.51 Collecting neo4j>=5.14.0 (from -r requirements-docker.txt (line 43))
#14 27.52   Downloading neo4j-6.1.0-py3-none-any.whl.metadata (5.3 kB)
#14 27.55 Collecting httpx>=0.26.0 (from -r requirements-docker.txt (line 46))
#14 27.56   Downloading httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
#14 27.64 Collecting openai>=1.10.0 (from -r requirements-docker.txt (line 49))
#14 27.65   Downloading openai-2.17.0-py3-none-any.whl.metadata (29 kB)
#14 27.72 Collecting langgraph>=0.0.40 (from -r requirements-docker.txt (line 52))
#14 27.73   Downloading langgraph-1.0.7-py3-none-any.whl.metadata (7.4 kB)
#14 27.80 Collecting langchain-core>=0.1.20 (from -r requirements-docker.txt (line 53))
#14 27.80   Downloading langchain_core-1.2.9-py3-none-any.whl.metadata (4.4 kB)
#14 27.82 Collecting structlog>=24.1.0 (from -r requirements-docker.txt (line 56))
#14 27.83   Downloading structlog-25.5.0-py3-none-any.whl.metadata (9.5 kB)
#14 27.86 Collecting anyio>=4.2.0 (from -r requirements-docker.txt (line 59))
#14 27.87   Downloading anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
#14 27.89 Collecting aiofiles>=23.2.0 (from -r requirements-docker.txt (line 60))
#14 27.90   Downloading aiofiles-25.1.0-py3-none-any.whl.metadata (6.3 kB)
#14 27.90 Requirement already satisfied: typing-extensions>=4.9.0 in /usr/local/lib/python3.12/site-packages (from -r requirements-docker.txt (line 63)) (4.15.0)
#14 27.97 Collecting twilio>=8.10.0 (from -r requirements-docker.txt (line 66))
#14 27.98   Downloading twilio-9.10.1-py2.py3-none-any.whl.metadata (13 kB)
#14 27.98 Requirement already satisfied: Jinja2>=3.1.2 in /usr/local/lib/python3.12/site-packages (from -r requirements-docker.txt (line 69)) (3.1.6)
#14 28.03 Collecting PyYAML>=6.0.1 (from -r requirements-docker.txt (line 72))
#14 28.04   Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
#14 28.22 Collecting cryptography>=41.0.0 (from -r requirements-docker.txt (line 75))
#14 28.23   Downloading cryptography-46.0.4-cp311-abi3-manylinux_2_34_x86_64.whl.metadata (5.7 kB)
#14 28.23 Requirement already satisfied: sympy>=1.12 in /usr/local/lib/python3.12/site-packages (from -r requirements-docker.txt (line 78)) (1.14.0)
#14 28.38 Collecting numpy>=1.24.0 (from -r requirements-docker.txt (line 79))
#14 28.39   Downloading numpy-2.4.2-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl.metadata (6.6 kB)
#14 28.40 Collecting sentence-transformers>=2.2.0 (from -r requirements-docker.txt (line 82))
#14 28.41   Downloading sentence_transformers-5.2.2-py3-none-any.whl.metadata (16 kB)
#14 28.44 Collecting mcp>=1.0.0 (from -r requirements-docker.txt (line 89))
#14 28.45   Downloading mcp-1.26.0-py3-none-any.whl.metadata (89 kB)
#14 28.49 Collecting prometheus_client>=0.19.0 (from -r requirements-docker.txt (line 92))
#14 28.50   Downloading prometheus_client-0.24.1-py3-none-any.whl.metadata (2.1 kB)
#14 28.54 Collecting opentelemetry-api>=1.21.0 (from -r requirements-docker.txt (line 95))
#14 28.55   Downloading opentelemetry_api-1.39.1-py3-none-any.whl.metadata (1.5 kB)
#14 28.58 Collecting opentelemetry-sdk>=1.21.0 (from -r requirements-docker.txt (line 96))
#14 28.59   Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl.metadata (1.5 kB)
#14 28.62 Collecting opentelemetry-exporter-otlp-proto-http>=1.21.0 (from -r requirements-docker.txt (line 97))
#14 28.63   Downloading opentelemetry_exporter_otlp_proto_http-1.39.1-py3-none-any.whl.metadata (2.4 kB)
#14 28.67 Collecting pytest>=7.4.0 (from -r requirements-docker.txt (line 100))
#14 28.68   Downloading pytest-9.0.2-py3-none-any.whl.metadata (7.6 kB)
#14 28.71 Collecting pytest-asyncio>=0.23.0 (from -r requirements-docker.txt (line 101))
#14 28.72   Downloading pytest_asyncio-1.3.0-py3-none-any.whl.metadata (4.1 kB)
#14 28.75 Collecting pytest-cov>=4.1.0 (from -r requirements-docker.txt (line 102))
#14 28.76   Downloading pytest_cov-7.0.0-py3-none-any.whl.metadata (31 kB)
#14 28.79 Collecting pytest-mock>=3.12.0 (from -r requirements-docker.txt (line 103))
#14 28.80   Downloading pytest_mock-3.15.1-py3-none-any.whl.metadata (3.9 kB)
#14 29.11 Collecting ruff>=0.4.0 (from -r requirements-docker.txt (line 104))
#14 29.12   Downloading ruff-0.15.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (26 kB)
#14 29.14 Collecting vulture>=2.11 (from -r requirements-docker.txt (line 105))
#14 29.15   Downloading vulture-2.14-py2.py3-none-any.whl.metadata (24 kB)
#14 29.22 Collecting mypy>=1.10.0 (from -r requirements-docker.txt (line 106))
#14 29.23   Downloading mypy-1.19.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.2 kB)
#14 29.24 Collecting python-multipart (from -r requirements-docker.txt (line 107))
#14 29.25   Downloading python_multipart-0.0.22-py3-none-any.whl.metadata (1.8 kB)
#14 29.28 Collecting urllib3<3 (from -r requirements-docker.txt (line 110))
#14 29.29   Downloading urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
#14 29.31 Collecting mutmut>=2.4.5 (from -r requirements-docker.txt (line 113))
#14 29.32   Downloading mutmut-3.4.0-py3-none-any.whl.metadata (9.2 kB)
#14 29.74 Collecting aiohttp>=3.9.0 (from -r requirements-docker.txt (line 116))
#14 29.75   Downloading aiohttp-3.13.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (8.1 kB)
#14 29.75 Requirement already satisfied: networkx>=3.0 in /usr/local/lib/python3.12/site-packages (from -r requirements-docker.txt (line 117)) (3.6.1)
#14 29.76 Collecting cachetools>=5.3.0 (from -r requirements-docker.txt (line 120))
#14 29.77   Downloading cachetools-7.0.0-py3-none-any.whl.metadata (5.6 kB)
#14 29.79 Collecting jsonschema>=4.21.0 (from -r requirements-docker.txt (line 123))
#14 29.80   Downloading jsonschema-4.26.0-py3-none-any.whl.metadata (7.6 kB)
#14 29.83 Collecting starlette<0.51.0,>=0.40.0 (from fastapi>=0.109.0->-r requirements-docker.txt (line 25))
#14 29.84   Downloading starlette-0.50.0-py3-none-any.whl.metadata (6.3 kB)
#14 29.85 Collecting typing-inspection>=0.4.2 (from fastapi>=0.109.0->-r requirements-docker.txt (line 25))
#14 29.86   Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
#14 29.88 Collecting annotated-doc>=0.0.2 (from fastapi>=0.109.0->-r requirements-docker.txt (line 25))
#14 29.89   Downloading annotated_doc-0.0.4-py3-none-any.whl.metadata (6.6 kB)
#14 29.91 Collecting idna>=2.8 (from anyio>=4.2.0->-r requirements-docker.txt (line 59))
#14 29.92   Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
#14 29.95 Collecting click>=7.0 (from uvicorn>=0.27.0->uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 29.96   Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
#14 29.98 Collecting h11>=0.8 (from uvicorn>=0.27.0->uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 29.99   Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
#14 30.01 Collecting annotated-types>=0.6.0 (from pydantic>=2.5.0->-r requirements-docker.txt (line 27))
#14 30.02   Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
#14 30.57 Collecting pydantic-core==2.41.5 (from pydantic>=2.5.0->-r requirements-docker.txt (line 27))
#14 30.58   Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (7.3 kB)
#14 30.66 Collecting greenlet>=1 (from sqlalchemy>=2.0.23->-r requirements-docker.txt (line 35))
#14 30.68   Downloading greenlet-3.3.1-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl.metadata (3.7 kB)
#14 30.71 Collecting pytz (from neo4j>=5.14.0->-r requirements-docker.txt (line 43))
#14 30.72   Downloading pytz-2025.2-py2.py3-none-any.whl.metadata (22 kB)
#14 30.73 Collecting certifi (from httpx>=0.26.0->-r requirements-docker.txt (line 46))
#14 30.74   Downloading certifi-2026.1.4-py3-none-any.whl.metadata (2.5 kB)
#14 30.76 Collecting httpcore==1.* (from httpx>=0.26.0->-r requirements-docker.txt (line 46))
#14 30.77   Downloading httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
#14 30.79 Collecting distro<2,>=1.7.0 (from openai>=1.10.0->-r requirements-docker.txt (line 49))
#14 30.80   Downloading distro-1.9.0-py3-none-any.whl.metadata (6.8 kB)
#14 30.88 Collecting jiter<1,>=0.10.0 (from openai>=1.10.0->-r requirements-docker.txt (line 49))
#14 30.89   Downloading jiter-0.13.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (5.2 kB)
#14 30.90 Collecting sniffio (from openai>=1.10.0->-r requirements-docker.txt (line 49))
#14 30.91   Downloading sniffio-1.3.1-py3-none-any.whl.metadata (3.9 kB)
#14 30.96 Collecting tqdm>4 (from openai>=1.10.0->-r requirements-docker.txt (line 49))
#14 30.97   Downloading tqdm-4.67.3-py3-none-any.whl.metadata (57 kB)
#14 31.03 Collecting langgraph-checkpoint<5.0.0,>=2.1.0 (from langgraph>=0.0.40->-r requirements-docker.txt (line 52))
#14 31.04   Downloading langgraph_checkpoint-4.0.0-py3-none-any.whl.metadata (4.9 kB)
#14 31.06 Collecting langgraph-prebuilt<1.1.0,>=1.0.7 (from langgraph>=0.0.40->-r requirements-docker.txt (line 52))
#14 31.07   Downloading langgraph_prebuilt-1.0.7-py3-none-any.whl.metadata (5.2 kB)
#14 31.10 Collecting langgraph-sdk<0.4.0,>=0.3.0 (from langgraph>=0.0.40->-r requirements-docker.txt (line 52))
#14 31.11   Downloading langgraph_sdk-0.3.4-py3-none-any.whl.metadata (1.6 kB)
#14 31.21 Collecting xxhash>=3.5.0 (from langgraph>=0.0.40->-r requirements-docker.txt (line 52))
#14 31.22   Downloading xxhash-3.6.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (13 kB)
#14 31.30 Collecting ormsgpack>=1.12.0 (from langgraph-checkpoint<5.0.0,>=2.1.0->langgraph>=0.0.40->-r requirements-docker.txt (line 52))
#14 31.31   Downloading ormsgpack-1.12.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (3.2 kB)
#14 31.59 Collecting orjson>=3.10.1 (from langgraph-sdk<0.4.0,>=0.3.0->langgraph>=0.0.40->-r requirements-docker.txt (line 52))
#14 31.60   Downloading orjson-3.11.7-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (41 kB)
#14 31.61 Collecting jsonpatch<2.0.0,>=1.33.0 (from langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.62   Downloading jsonpatch-1.33-py2.py3-none-any.whl.metadata (3.0 kB)
#14 31.66 Collecting langsmith<1.0.0,>=0.3.45 (from langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.68   Downloading langsmith-0.6.9-py3-none-any.whl.metadata (15 kB)
#14 31.68 Requirement already satisfied: packaging>=23.2.0 in /usr/local/lib/python3.12/site-packages (from langchain-core>=0.1.20->-r requirements-docker.txt (line 53)) (26.0)
#14 31.69 Collecting tenacity!=8.4.0,<10.0.0,>=8.1.0 (from langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.70   Downloading tenacity-9.1.3-py3-none-any.whl.metadata (1.2 kB)
#14 31.76 Collecting uuid-utils<1.0,>=0.12.0 (from langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.77   Downloading uuid_utils-0.14.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.9 kB)
#14 31.79 Collecting jsonpointer>=1.9 (from jsonpatch<2.0.0,>=1.33.0->langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.80   Downloading jsonpointer-3.0.0-py2.py3-none-any.whl.metadata (2.3 kB)
#14 31.83 Collecting requests-toolbelt>=1.0.0 (from langsmith<1.0.0,>=0.3.45->langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.84   Downloading requests_toolbelt-1.0.0-py2.py3-none-any.whl.metadata (14 kB)
#14 31.88 Collecting requests>=2.0.0 (from langsmith<1.0.0,>=0.3.45->langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.89   Downloading requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
#14 31.98 Collecting zstandard>=0.23.0 (from langsmith<1.0.0,>=0.3.45->langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 31.99   Downloading zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (3.3 kB)
#14 32.02 Collecting PyJWT<3.0.0,>=2.0.0 (from twilio>=8.10.0->-r requirements-docker.txt (line 66))
#14 32.03   Downloading pyjwt-2.11.0-py3-none-any.whl.metadata (4.0 kB)
#14 32.06 Collecting aiohttp-retry>=2.8.3 (from twilio>=8.10.0->-r requirements-docker.txt (line 66))
#14 32.07   Downloading aiohttp_retry-2.9.1-py3-none-any.whl.metadata (8.8 kB)
#14 32.08 Requirement already satisfied: MarkupSafe>=2.0 in /usr/local/lib/python3.12/site-packages (from Jinja2>=3.1.2->-r requirements-docker.txt (line 69)) (2.1.5)
#14 32.18 Collecting cffi>=2.0.0 (from cryptography>=41.0.0->-r requirements-docker.txt (line 75))
#14 32.19   Downloading cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.6 kB)
#14 32.20 Requirement already satisfied: mpmath<1.4,>=1.1.0 in /usr/local/lib/python3.12/site-packages (from sympy>=1.12->-r requirements-docker.txt (line 78)) (1.3.0)
#14 32.25 Collecting transformers<6.0.0,>=4.41.0 (from sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 32.26   Downloading transformers-5.1.0-py3-none-any.whl.metadata (31 kB)
#14 32.34 Collecting huggingface-hub>=0.20.0 (from sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 32.35   Downloading huggingface_hub-1.4.0-py3-none-any.whl.metadata (13 kB)
#14 32.37 Requirement already satisfied: torch>=1.11.0 in /usr/local/lib/python3.12/site-packages (from sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82)) (2.10.0+cpu)
#14 32.44 Collecting scikit-learn (from sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 32.45   Downloading scikit_learn-1.8.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl.metadata (11 kB)
#14 32.55 Collecting scipy (from sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 32.56   Downloading scipy-1.17.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl.metadata (62 kB)
#14 32.95 Collecting regex!=2019.12.17 (from transformers<6.0.0,>=4.41.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 32.96   Downloading regex-2026.1.15-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (40 kB)
#14 33.05 Collecting tokenizers<=0.23.0,>=0.22.0 (from transformers<6.0.0,>=4.41.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 33.06   Downloading tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (7.3 kB)
#14 33.08 Collecting typer-slim (from transformers<6.0.0,>=4.41.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 33.09   Downloading typer_slim-0.21.1-py3-none-any.whl.metadata (16 kB)
#14 33.17 Collecting safetensors>=0.4.3 (from transformers<6.0.0,>=4.41.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 33.18   Downloading safetensors-0.7.0-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.1 kB)
#14 33.19 Requirement already satisfied: filelock in /usr/local/lib/python3.12/site-packages (from huggingface-hub>=0.20.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82)) (3.20.0)
#14 33.19 Requirement already satisfied: fsspec>=2023.5.0 in /usr/local/lib/python3.12/site-packages (from huggingface-hub>=0.20.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82)) (2025.12.0)
#14 33.22 Collecting hf-xet<2.0.0,>=1.2.0 (from huggingface-hub>=0.20.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 33.23   Downloading hf_xet-1.2.0-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.9 kB)
#14 33.24 Collecting shellingham (from huggingface-hub>=0.20.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 33.25   Downloading shellingham-1.5.4-py2.py3-none-any.whl.metadata (3.5 kB)
#14 33.27 Collecting httpx-sse>=0.4 (from mcp>=1.0.0->-r requirements-docker.txt (line 89))
#14 33.28   Downloading httpx_sse-0.4.3-py3-none-any.whl.metadata (9.7 kB)
#14 33.32 Collecting sse-starlette>=1.6.1 (from mcp>=1.0.0->-r requirements-docker.txt (line 89))
#14 33.33   Downloading sse_starlette-3.2.0-py3-none-any.whl.metadata (12 kB)
#14 33.37 Collecting importlib-metadata<8.8.0,>=6.0 (from opentelemetry-api>=1.21.0->-r requirements-docker.txt (line 95))
#14 33.38   Downloading importlib_metadata-8.7.1-py3-none-any.whl.metadata (4.7 kB)
#14 33.41 Collecting zipp>=3.20 (from importlib-metadata<8.8.0,>=6.0->opentelemetry-api>=1.21.0->-r requirements-docker.txt (line 95))
#14 33.42   Downloading zipp-3.23.0-py3-none-any.whl.metadata (3.6 kB)
#14 33.45 Collecting opentelemetry-semantic-conventions==0.60b1 (from opentelemetry-sdk>=1.21.0->-r requirements-docker.txt (line 96))
#14 33.46   Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl.metadata (2.4 kB)
#14 33.50 Collecting googleapis-common-protos~=1.52 (from opentelemetry-exporter-otlp-proto-http>=1.21.0->-r requirements-docker.txt (line 97))
#14 33.51   Downloading googleapis_common_protos-1.72.0-py3-none-any.whl.metadata (9.4 kB)
#14 33.53 Collecting opentelemetry-exporter-otlp-proto-common==1.39.1 (from opentelemetry-exporter-otlp-proto-http>=1.21.0->-r requirements-docker.txt (line 97))
#14 33.54   Downloading opentelemetry_exporter_otlp_proto_common-1.39.1-py3-none-any.whl.metadata (1.8 kB)
#14 33.57 Collecting opentelemetry-proto==1.39.1 (from opentelemetry-exporter-otlp-proto-http>=1.21.0->-r requirements-docker.txt (line 97))
#14 33.58   Downloading opentelemetry_proto-1.39.1-py3-none-any.whl.metadata (2.3 kB)
#14 33.73 Collecting protobuf<7.0,>=5.0 (from opentelemetry-proto==1.39.1->opentelemetry-exporter-otlp-proto-http>=1.21.0->-r requirements-docker.txt (line 97))
#14 33.74   Downloading protobuf-6.33.5-cp39-abi3-manylinux2014_x86_64.whl.metadata (593 bytes)
#14 33.80 Collecting charset_normalizer<4,>=2 (from requests>=2.0.0->langsmith<1.0.0,>=0.3.45->langchain-core>=0.1.20->-r requirements-docker.txt (line 53))
#14 33.81   Downloading charset_normalizer-3.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (37 kB)
#14 33.83 Collecting iniconfig>=1.0.1 (from pytest>=7.4.0->-r requirements-docker.txt (line 100))
#14 33.84   Downloading iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
#14 33.86 Collecting pluggy<2,>=1.5 (from pytest>=7.4.0->-r requirements-docker.txt (line 100))
#14 33.86   Downloading pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
#14 33.89 Collecting pygments>=2.7.2 (from pytest>=7.4.0->-r requirements-docker.txt (line 100))
#14 33.90   Downloading pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
#14 34.31 Collecting coverage>=7.10.6 (from coverage[toml]>=7.10.6->pytest-cov>=4.1.0->-r requirements-docker.txt (line 102))
#14 34.32   Downloading coverage-7.13.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (8.5 kB)
#14 34.34 Collecting mypy_extensions>=1.0.0 (from mypy>=1.10.0->-r requirements-docker.txt (line 106))
#14 34.35   Downloading mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
#14 34.36 Collecting pathspec>=0.9.0 (from mypy>=1.10.0->-r requirements-docker.txt (line 106))
#14 34.37   Downloading pathspec-1.0.4-py3-none-any.whl.metadata (13 kB)
#14 34.44 Collecting librt>=0.6.2 (from mypy>=1.10.0->-r requirements-docker.txt (line 106))
#14 34.45   Downloading librt-0.7.8-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (1.3 kB)
#14 34.51 Collecting libcst>=1.8.5 (from mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 34.52   Downloading libcst-1.8.6-cp312-cp312-manylinux_2_28_x86_64.whl.metadata (15 kB)
#14 34.56 Collecting setproctitle>=1.1.0 (from mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 34.57   Downloading setproctitle-1.3.7-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (10 kB)
#14 34.62 Collecting textual>=1.0.0 (from mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 34.63   Downloading textual-7.5.0-py3-none-any.whl.metadata (9.1 kB)
#14 34.65 Collecting aiohappyeyeballs>=2.5.0 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 34.66   Downloading aiohappyeyeballs-2.6.1-py3-none-any.whl.metadata (5.9 kB)
#14 34.67 Collecting aiosignal>=1.4.0 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 34.68   Downloading aiosignal-1.4.0-py3-none-any.whl.metadata (3.7 kB)
#14 34.71 Collecting attrs>=17.3.0 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 34.72   Downloading attrs-25.4.0-py3-none-any.whl.metadata (10 kB)
#14 34.80 Collecting frozenlist>=1.1.1 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 34.81   Downloading frozenlist-1.8.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (20 kB)
#14 35.00 Collecting multidict<7.0,>=4.5 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 35.01   Downloading multidict-6.7.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (5.3 kB)
#14 35.06 Collecting propcache>=0.2.0 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 35.07   Downloading propcache-0.4.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (13 kB)
#14 35.26 Collecting yarl<2.0,>=1.17.0 (from aiohttp>=3.9.0->-r requirements-docker.txt (line 116))
#14 35.27   Downloading yarl-1.22.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (75 kB)
#14 35.30 Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=4.21.0->-r requirements-docker.txt (line 123))
#14 35.31   Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
#14 35.33 Collecting referencing>=0.28.4 (from jsonschema>=4.21.0->-r requirements-docker.txt (line 123))
#14 35.34   Downloading referencing-0.37.0-py3-none-any.whl.metadata (2.8 kB)
#14 35.69 Collecting rpds-py>=0.25.0 (from jsonschema>=4.21.0->-r requirements-docker.txt (line 123))
#14 35.70   Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.1 kB)
#14 35.72 Collecting pycparser (from cffi>=2.0.0->cryptography>=41.0.0->-r requirements-docker.txt (line 75))
#14 35.73   Downloading pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
#14 35.86 Collecting psycopg-binary==3.3.2 (from psycopg[binary]>=3.1.14->-r requirements-docker.txt (line 34))
#14 35.87   Downloading psycopg_binary-3.3.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.7 kB)
#14 35.91 Collecting markdown-it-py>=2.1.0 (from markdown-it-py[linkify]>=2.1.0->textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 35.92   Downloading markdown_it_py-4.0.0-py3-none-any.whl.metadata (7.3 kB)
#14 35.93 Collecting mdit-py-plugins (from textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 35.94   Downloading mdit_py_plugins-0.5.0-py3-none-any.whl.metadata (2.8 kB)
#14 35.96 Collecting platformdirs<5,>=3.6.0 (from textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 35.97   Downloading platformdirs-4.5.1-py3-none-any.whl.metadata (12 kB)
#14 36.01 Collecting rich>=14.2.0 (from textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 36.02   Downloading rich-14.3.2-py3-none-any.whl.metadata (18 kB)
#14 36.04 Collecting mdurl~=0.1 (from markdown-it-py>=2.1.0->markdown-it-py[linkify]>=2.1.0->textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 36.05   Downloading mdurl-0.1.2-py3-none-any.whl.metadata (1.6 kB)
#14 36.08 Collecting linkify-it-py<3,>=1 (from markdown-it-py[linkify]>=2.1.0->textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 36.09   Downloading linkify_it_py-2.0.3-py3-none-any.whl.metadata (8.5 kB)
#14 36.11 Collecting uc-micro-py (from linkify-it-py<3,>=1->markdown-it-py[linkify]>=2.1.0->textual>=1.0.0->mutmut>=2.4.5->-r requirements-docker.txt (line 113))
#14 36.12   Downloading uc_micro_py-1.0.3-py3-none-any.whl.metadata (2.0 kB)
#14 36.13 Requirement already satisfied: setuptools in /usr/local/lib/python3.12/site-packages (from torch>=1.11.0->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82)) (80.10.2)
#14 36.19 Collecting httptools>=0.6.3 (from uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 36.20   Downloading httptools-0.7.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (3.5 kB)
#14 36.26 Collecting uvloop>=0.15.1 (from uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 36.27   Downloading uvloop-0.22.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (4.9 kB)
#14 36.36 Collecting watchfiles>=0.13 (from uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 36.37   Downloading watchfiles-1.1.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.9 kB)
#14 36.43 Collecting websockets>=10.4 (from uvicorn[standard]>=0.27.0->-r requirements-docker.txt (line 26))
#14 36.44   Downloading websockets-16.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (6.8 kB)
#14 36.48 Collecting joblib>=1.3.0 (from scikit-learn->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 36.48   Downloading joblib-1.5.3-py3-none-any.whl.metadata (5.5 kB)
#14 36.50 Collecting threadpoolctl>=3.2.0 (from scikit-learn->sentence-transformers>=2.2.0->-r requirements-docker.txt (line 82))
#14 36.50   Downloading threadpoolctl-3.6.0-py3-none-any.whl.metadata (13 kB)
#14 36.54 Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
#14 36.55 Downloading fastapi-0.128.2-py3-none-any.whl (104 kB)
#14 36.56 Downloading starlette-0.50.0-py3-none-any.whl (74 kB)
#14 36.57 Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
#14 36.58 Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
#14 36.59 Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
#14 36.61 Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.1 MB)
#14 36.63    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 128.5 MB/s  0:00:00
#14 36.65 Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
#14 36.66 Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
#14 36.67 Downloading psycopg-3.3.2-py3-none-any.whl (212 kB)
#14 36.69 Downloading sqlalchemy-2.0.46-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (3.3 MB)
#14 36.71    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.3/3.3 MB 248.0 MB/s  0:00:00
#14 36.72 Downloading asyncpg-0.31.0-cp312-cp312-manylinux_2_28_x86_64.whl (3.5 MB)
#14 36.74    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.5/3.5 MB 200.5 MB/s  0:00:00
#14 36.76 Downloading pgvector-0.4.2-py3-none-any.whl (27 kB)
#14 36.77 Downloading redis-7.1.0-py3-none-any.whl (354 kB)
#14 36.78 Downloading neo4j-6.1.0-py3-none-any.whl (325 kB)
#14 36.79 Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
#14 36.80 Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
#14 36.81 Downloading openai-2.17.0-py3-none-any.whl (1.1 MB)
#14 36.82    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 249.4 MB/s  0:00:00
#14 36.83 Downloading distro-1.9.0-py3-none-any.whl (20 kB)
#14 36.84 Downloading jiter-0.13.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (360 kB)
#14 36.85 Downloading langgraph-1.0.7-py3-none-any.whl (157 kB)
#14 36.86 Downloading langgraph_checkpoint-4.0.0-py3-none-any.whl (46 kB)
#14 36.87 Downloading langgraph_prebuilt-1.0.7-py3-none-any.whl (35 kB)
#14 36.88 Downloading langgraph_sdk-0.3.4-py3-none-any.whl (67 kB)
#14 36.89 Downloading langchain_core-1.2.9-py3-none-any.whl (496 kB)
#14 36.90 Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (807 kB)
#14 36.91    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 807.9/807.9 kB 322.9 MB/s  0:00:00
#14 36.92 Downloading jsonpatch-1.33-py2.py3-none-any.whl (12 kB)
#14 36.93 Downloading langsmith-0.6.9-py3-none-any.whl (319 kB)
#14 36.94 Downloading tenacity-9.1.3-py3-none-any.whl (28 kB)
#14 36.95 Downloading uuid_utils-0.14.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (341 kB)
#14 36.96 Downloading structlog-25.5.0-py3-none-any.whl (72 kB)
#14 36.97 Downloading aiofiles-25.1.0-py3-none-any.whl (14 kB)
#14 36.99 Downloading twilio-9.10.1-py2.py3-none-any.whl (2.3 MB)
#14 37.00    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB 294.2 MB/s  0:00:00
#14 37.01 Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
#14 37.02 Downloading cryptography-46.0.4-cp311-abi3-manylinux_2_34_x86_64.whl (4.5 MB)
#14 37.04    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.5/4.5 MB 310.1 MB/s  0:00:00
#14 37.05 Downloading numpy-2.4.2-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (16.6 MB)
#14 37.13    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 16.6/16.6 MB 218.4 MB/s  0:00:00
#14 37.14 Downloading sentence_transformers-5.2.2-py3-none-any.whl (494 kB)
#14 37.16 Downloading transformers-5.1.0-py3-none-any.whl (10.3 MB)
#14 37.21    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.3/10.3 MB 212.5 MB/s  0:00:00
#14 37.22 Downloading huggingface_hub-1.4.0-py3-none-any.whl (553 kB)
#14 37.22    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 553.2/553.2 kB 276.1 MB/s  0:00:00
#14 37.24 Downloading hf_xet-1.2.0-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.3 MB)
#14 37.25    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.3/3.3 MB 314.3 MB/s  0:00:00
#14 37.26 Downloading tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.3 MB)
#14 37.28    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.3/3.3 MB 281.0 MB/s  0:00:00
#14 37.30 Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
#14 37.31 Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
#14 37.32 Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
#14 37.33 Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
#14 37.34 Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
#14 37.35 Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
#14 37.35 Downloading opentelemetry_exporter_otlp_proto_http-1.39.1-py3-none-any.whl (19 kB)
#14 37.36 Downloading opentelemetry_exporter_otlp_proto_common-1.39.1-py3-none-any.whl (18 kB)
#14 37.37 Downloading opentelemetry_proto-1.39.1-py3-none-any.whl (72 kB)
#14 37.38 Downloading googleapis_common_protos-1.72.0-py3-none-any.whl (297 kB)
#14 37.39 Downloading protobuf-6.33.5-cp39-abi3-manylinux2014_x86_64.whl (323 kB)
#14 37.40 Downloading requests-2.32.5-py3-none-any.whl (64 kB)
#14 37.41 Downloading charset_normalizer-3.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (153 kB)
#14 37.42 Downloading idna-3.11-py3-none-any.whl (71 kB)
#14 37.42 Downloading pytest-9.0.2-py3-none-any.whl (374 kB)
#14 37.43 Downloading pluggy-1.6.0-py3-none-any.whl (20 kB)
#14 37.44 Downloading pytest_asyncio-1.3.0-py3-none-any.whl (15 kB)
#14 37.45 Downloading pytest_cov-7.0.0-py3-none-any.whl (22 kB)
#14 37.46 Downloading pytest_mock-3.15.1-py3-none-any.whl (10 kB)
#14 37.47 Downloading ruff-0.15.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (11.1 MB)
#14 37.53    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.1/11.1 MB 194.0 MB/s  0:00:00
#14 37.54 Downloading vulture-2.14-py2.py3-none-any.whl (28 kB)
#14 37.55 Downloading mypy-1.19.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (13.6 MB)
#14 37.61    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.6/13.6 MB 246.3 MB/s  0:00:00
#14 37.62 Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
#14 37.63 Downloading mutmut-3.4.0-py3-none-any.whl (29 kB)
#14 37.64 Downloading aiohttp-3.13.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.8 MB)
#14 37.65    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 306.4 MB/s  0:00:00
#14 37.66 Downloading multidict-6.7.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (256 kB)
#14 37.67 Downloading yarl-1.22.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (377 kB)
#14 37.68 Downloading cachetools-7.0.0-py3-none-any.whl (13 kB)
#14 37.69 Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
#14 37.70 Downloading aiohappyeyeballs-2.6.1-py3-none-any.whl (15 kB)
#14 37.71 Downloading aiohttp_retry-2.9.1-py3-none-any.whl (10.0 kB)
#14 37.72 Downloading aiosignal-1.4.0-py3-none-any.whl (7.5 kB)
#14 37.73 Downloading annotated_doc-0.0.4-py3-none-any.whl (5.3 kB)
#14 37.75 Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
#14 37.76 Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
#14 37.77 Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
#14 37.78 Downloading cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (219 kB)
#14 37.79 Downloading click-8.3.1-py3-none-any.whl (108 kB)
#14 37.80 Downloading coverage-7.13.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (254 kB)
#14 37.81 Downloading frozenlist-1.8.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (242 kB)
#14 37.82 Downloading greenlet-3.3.1-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl (609 kB)
#14 37.83    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 609.9/609.9 kB 258.9 MB/s  0:00:00
#14 37.84 Downloading h11-0.16.0-py3-none-any.whl (37 kB)
#14 37.85 Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
#14 37.86 Downloading iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
#14 37.87 Downloading jsonpointer-3.0.0-py2.py3-none-any.whl (7.6 kB)
#14 37.88 Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
#14 37.89 Downloading libcst-1.8.6-cp312-cp312-manylinux_2_28_x86_64.whl (2.3 MB)
#14 37.90    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB 261.7 MB/s  0:00:00
#14 37.92 Downloading librt-0.7.8-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (192 kB)
#14 37.93 Downloading mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
#14 37.94 Downloading orjson-3.11.7-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (133 kB)
#14 37.95 Downloading ormsgpack-1.12.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (212 kB)
#14 37.96 Downloading pathspec-1.0.4-py3-none-any.whl (55 kB)
#14 37.97 Downloading propcache-0.4.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (221 kB)
#14 37.98 Downloading psycopg_binary-3.3.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (5.1 MB)
#14 38.01    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.1/5.1 MB 232.3 MB/s  0:00:00
#14 38.02 Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
#14 38.03    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 280.3 MB/s  0:00:00
#14 38.04 Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
#14 38.05 Downloading regex-2026.1.15-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (803 kB)
#14 38.05    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 803.6/803.6 kB 321.7 MB/s  0:00:00
#14 38.06 Downloading requests_toolbelt-1.0.0-py2.py3-none-any.whl (54 kB)
#14 38.07 Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (394 kB)
#14 38.09 Downloading safetensors-0.7.0-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (507 kB)
#14 38.10 Downloading setproctitle-1.3.7-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (32 kB)
#14 38.11 Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
#14 38.12 Downloading textual-7.5.0-py3-none-any.whl (718 kB)
#14 38.13    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 718.2/718.2 kB 308.8 MB/s  0:00:00
#14 38.14 Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
#14 38.15 Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
#14 38.16 Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
#14 38.17 Downloading linkify_it_py-2.0.3-py3-none-any.whl (19 kB)
#14 38.18 Downloading rich-14.3.2-py3-none-any.whl (309 kB)
#14 38.19 Downloading tqdm-4.67.3-py3-none-any.whl (78 kB)
#14 38.20 Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
#14 38.21 Downloading httptools-0.7.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (517 kB)
#14 38.23 Downloading uvloop-0.22.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.4 MB)
#14 38.26    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.4/4.4 MB 209.8 MB/s  0:00:00
#14 38.27 Downloading watchfiles-1.1.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (456 kB)
#14 38.28 Downloading websockets-16.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (184 kB)
#14 38.29 Downloading xxhash-3.6.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (193 kB)
#14 38.31 Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
#14 38.32 Downloading zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (5.5 MB)
#14 38.35    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.5/5.5 MB 257.9 MB/s  0:00:00
#14 38.36 Downloading mdit_py_plugins-0.5.0-py3-none-any.whl (57 kB)
#14 38.37 Downloading pycparser-3.0-py3-none-any.whl (48 kB)
#14 38.38 Downloading pytz-2025.2-py2.py3-none-any.whl (509 kB)
#14 38.39 Downloading scikit_learn-1.8.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (8.9 MB)
#14 38.44    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.9/8.9 MB 203.1 MB/s  0:00:00
#14 38.45 Downloading joblib-1.5.3-py3-none-any.whl (309 kB)
#14 38.46 Downloading scipy-1.17.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (35.0 MB)
#14 38.61    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 35.0/35.0 MB 240.4 MB/s  0:00:00
#14 38.62 Downloading threadpoolctl-3.6.0-py3-none-any.whl (18 kB)
#14 38.63 Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
#14 38.64 Downloading sniffio-1.3.1-py3-none-any.whl (10 kB)
#14 38.65 Downloading typer_slim-0.21.1-py3-none-any.whl (47 kB)
#14 38.66 Downloading uc_micro_py-1.0.3-py3-none-any.whl (6.2 kB)
#14 39.11 Installing collected packages: pytz, zstandard, zipp, xxhash, websockets, vulture, uvloop, uuid-utils, urllib3, uc-micro-py, typing-inspection, tqdm, threadpoolctl, tenacity, structlog, sniffio, shellingham, setproctitle, safetensors, ruff, rpds-py, regex, redis, PyYAML, python-multipart, python-dotenv, PyJWT, pygments, pydantic-core, pycparser, psycopg-binary, psycopg, protobuf, propcache, prometheus_client, pluggy, platformdirs, pathspec, ormsgpack, orjson, numpy, neo4j, mypy_extensions, multidict, mdurl, librt, jsonpointer, joblib, jiter, iniconfig, idna, httpx-sse, httptools, hf-xet, h11, greenlet, frozenlist, distro, coverage, click, charset_normalizer, certifi, cachetools, attrs, asyncpg, annotated-types, annotated-doc, aiohappyeyeballs, aiofiles, yarl, uvicorn, typer-slim, sqlalchemy, scipy, requests, referencing, pytest, pydantic, pgvector, opentelemetry-proto, mypy, markdown-it-py, linkify-it-py, libcst, jsonpatch, importlib-metadata, httpcore, googleapis-common-protos, cffi, anyio, aiosignal, watchfiles, starlette, scikit-learn, rich, requests-toolbelt, pytest-mock, pytest-cov, pytest-asyncio, pydantic-settings, opentelemetry-exporter-otlp-proto-common, opentelemetry-api, mdit-py-plugins, jsonschema-specifications, httpx, cryptography, aiohttp, textual, sse-starlette, opentelemetry-semantic-conventions, openai, langsmith, langgraph-sdk, jsonschema, huggingface-hub, fastapi, aiohttp-retry, twilio, tokenizers, opentelemetry-sdk, mutmut, mcp, langchain-core, transformers, opentelemetry-exporter-otlp-proto-http, langgraph-checkpoint, sentence-transformers, langgraph-prebuilt, langgraph
#14 62.18 
#14 62.19 Successfully installed PyJWT-2.11.0 PyYAML-6.0.3 aiofiles-25.1.0 aiohappyeyeballs-2.6.1 aiohttp-3.13.3 aiohttp-retry-2.9.1 aiosignal-1.4.0 annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.12.1 asyncpg-0.31.0 attrs-25.4.0 cachetools-7.0.0 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 coverage-7.13.3 cryptography-46.0.4 distro-1.9.0 fastapi-0.128.2 frozenlist-1.8.0 googleapis-common-protos-1.72.0 greenlet-3.3.1 h11-0.16.0 hf-xet-1.2.0 httpcore-1.0.9 httptools-0.7.1 httpx-0.28.1 httpx-sse-0.4.3 huggingface-hub-1.4.0 idna-3.11 importlib-metadata-8.7.1 iniconfig-2.3.0 jiter-0.13.0 joblib-1.5.3 jsonpatch-1.33 jsonpointer-3.0.0 jsonschema-4.26.0 jsonschema-specifications-2025.9.1 langchain-core-1.2.9 langgraph-1.0.7 langgraph-checkpoint-4.0.0 langgraph-prebuilt-1.0.7 langgraph-sdk-0.3.4 langsmith-0.6.9 libcst-1.8.6 librt-0.7.8 linkify-it-py-2.0.3 markdown-it-py-4.0.0 mcp-1.26.0 mdit-py-plugins-0.5.0 mdurl-0.1.2 multidict-6.7.1 mutmut-3.4.0 mypy-1.19.1 mypy_extensions-1.1.0 neo4j-6.1.0 numpy-2.4.2 openai-2.17.0 opentelemetry-api-1.39.1 opentelemetry-exporter-otlp-proto-common-1.39.1 opentelemetry-exporter-otlp-proto-http-1.39.1 opentelemetry-proto-1.39.1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 orjson-3.11.7 ormsgpack-1.12.2 pathspec-1.0.4 pgvector-0.4.2 platformdirs-4.5.1 pluggy-1.6.0 prometheus_client-0.24.1 propcache-0.4.1 protobuf-6.33.5 psycopg-3.3.2 psycopg-binary-3.3.2 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pygments-2.19.2 pytest-9.0.2 pytest-asyncio-1.3.0 pytest-cov-7.0.0 pytest-mock-3.15.1 python-dotenv-1.2.1 python-multipart-0.0.22 pytz-2025.2 redis-7.1.0 referencing-0.37.0 regex-2026.1.15 requests-2.32.5 requests-toolbelt-1.0.0 rich-14.3.2 rpds-py-0.30.0 ruff-0.15.0 safetensors-0.7.0 scikit-learn-1.8.0 scipy-1.17.0 sentence-transformers-5.2.2 setproctitle-1.3.7 shellingham-1.5.4 sniffio-1.3.1 sqlalchemy-2.0.46 sse-starlette-3.2.0 starlette-0.50.0 structlog-25.5.0 tenacity-9.1.3 textual-7.5.0 threadpoolctl-3.6.0 tokenizers-0.22.2 tqdm-4.67.3 transformers-5.1.0 twilio-9.10.1 typer-slim-0.21.1 typing-inspection-0.4.2 uc-micro-py-1.0.3 urllib3-2.6.3 uuid-utils-0.14.0 uvicorn-0.40.0 uvloop-0.22.1 vulture-2.14 watchfiles-1.1.1 websockets-16.0 xxhash-3.6.0 yarl-1.22.0 zipp-3.23.0 zstandard-0.25.0
#14 62.19 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#14 64.30 Files removed: 24 (3.3 MB)
#14 64.30 Directories removed: 0
#14 DONE 65.1s

#28 [l9-api production 3/4] COPY --chown=l9user:l9user . /app/
#28 DONE 0.4s

#29 [l9-bootstrap production 4/4] RUN test -f /app/api/server.py || (echo "ERROR: api/server.py not found" && exit 1) &&     test -f /app/requirements-docker.txt || (echo "ERROR: requirements-docker.txt not found" && exit 1)
#29 DONE 0.3s

#30 [l9-api] exporting to image
#30 exporting layers
#30 ...

#31 [l9-bootstrap] exporting to image
#31 ...

#30 [l9-api] exporting to image
#30 exporting layers 12.3s done
#30 writing image sha256:ee6cb245d131686891fddb61f6d130355a3a8e023fe5938dfe496dacc0e210e3 done
#30 naming to ghcr.io/cryptoxdog/l9-api:4.1.0 done
#30 DONE 12.3s

#31 [l9-bootstrap] exporting to image
#31 exporting layers 12.3s done
#31 writing image sha256:1282b4451ddd752292624d78f1397c46ab62cbfeb2cc91582dcc62564b16840f done
#31 naming to ghcr.io/cryptoxdog/l9-api:4.1.0 done
#31 DONE 12.3s

#32 [l9-bootstrap] resolving provenance for metadata file
#32 DONE 0.0s

#33 [l9-api] resolving provenance for metadata file
#33 DONE 0.0s
 Image ghcr.io/cryptoxdog/l9-api:4.1.0 Built 
 Image ghcr.io/cryptoxdog/l9-api:4.1.0 Built 
 Image ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0 Built 
time="2026-02-06T08:18:37Z" level=warning msg="The \"GRAFANA_PASSWORD\" variable is not set. Defaulting to a blank string."
 Network l9-network Creating 
 Network l9-network Created 
 Container l9-neo4j Creating 
 Container l9-prometheus Creating 
 Container l9-postgres Creating 
 Container l9-redis Creating 
 Container l9-jaeger Creating 
 Container l9-postgres Created 
 Container l9-neo4j Created 
 Container l9-redis Created 
 Container l9-bootstrap Creating 
 Container l9-l9-mcp-memory-1 Creating 
 Container l9-prometheus Created 
 Container l9-grafana Creating 
 Container l9-jaeger Created 
 Container l9-grafana Created 
 Container l9-bootstrap Created 
 Container l9-l9-api-1 Creating 
 Container l9-l9-mcp-memory-1 Created 
 Container l9-l9-api-1 Created 
 Container l9-nginx-1 Creating 
 Container l9-nginx-1 Created 
 Container l9-neo4j Starting 
 Container l9-prometheus Starting 
 Container l9-jaeger Starting 
 Container l9-postgres Starting 
 Container l9-redis Starting 
 Container l9-redis Started 
 Container l9-prometheus Started 
 Container l9-prometheus Waiting 
 Container l9-postgres Started 
 Container l9-neo4j Started 
 Container l9-postgres Waiting 
 Container l9-redis Waiting 
 Container l9-neo4j Waiting 
 Container l9-redis Waiting 
 Container l9-neo4j Waiting 
 Container l9-postgres Waiting 
 Container l9-jaeger Started 
 Container l9-redis Healthy 
 Container l9-redis Healthy 
 Container l9-postgres Healthy 
 Container l9-postgres Healthy 
 Container l9-prometheus Healthy 
 Container l9-grafana Starting 
 Container l9-grafana Started 
 Container l9-neo4j Healthy 
 Container l9-l9-mcp-memory-1 Starting 
 Container l9-neo4j Healthy 
 Container l9-bootstrap Starting 
 Container l9-l9-mcp-memory-1 Started 
 Container l9-bootstrap Started 
 Container l9-postgres Waiting 
 Container l9-redis Waiting 
 Container l9-neo4j Waiting 
 Container l9-bootstrap Waiting 
 Container l9-redis Healthy 
 Container l9-neo4j Healthy 
 Container l9-postgres Healthy 
 Container l9-bootstrap Exited 
 Container l9-l9-api-1 Starting 
 Container l9-l9-api-1 Started 
 Container l9-nginx-1 Starting 
 Container l9-nginx-1 Started 
./10X_Deploy_Script.sh: line 316: k: command not found
