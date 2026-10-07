# Source with bash; only completed selected state is loaded.
_cwe_old_install=${CUBRID:-}
for _cwe_var in PATH LD_LIBRARY_PATH; do
    _cwe_value=${!_cwe_var:-}
    _cwe_result=
    IFS=: read -r -a _cwe_parts <<< "$_cwe_value"
    for _cwe_part in "${_cwe_parts[@]}"; do
        if [[ -n "$_cwe_old_install" && ( "$_cwe_part" == "$_cwe_old_install/bin" || "$_cwe_part" == "$_cwe_old_install/lib" || "$_cwe_part" == "$_cwe_old_install/cci/lib" ) ]]; then
            continue
        fi
        _cwe_result=${_cwe_result:+$_cwe_result:}$_cwe_part
    done
    export "$_cwe_var=$_cwe_result"
done
for _cwe_name in ${!CUBRID@}; do
    [[ "$_cwe_name" == CUBRID_BUILD_DIR ]] || unset "$_cwe_name"
done
unset _cwe_old_install _cwe_var _cwe_value _cwe_result _cwe_parts _cwe_part _cwe_name LD_PRELOAD
export CUBRID_RUNTIME_READY=0
if ! python3 -c 'import json,os,sys; s=json.load(open(sys.argv[1])); sys.exit(not (s.get("status")=="ready" and s.get("worktree")==sys.argv[2] and s.get("install")==sys.argv[3] and s.get("preset")==sys.argv[4] and os.environ.get("PRESET_MODE",sys.argv[4])==sys.argv[4]))' /home/vimkim/gh/cb/pr7925-01-stored-rows/.cub-workenv/state.json /home/vimkim/gh/cb/pr7925-01-stored-rows /home/vimkim/.cub/install/pr7925-01-stored-rows/debug_gcc debug_gcc; then
  echo 'cub-workenv: incomplete or mismatched environment; run doctor' >&2
  return 1
fi
export CUBRID=/home/vimkim/.cub/install/pr7925-01-stored-rows/debug_gcc
export CUBRID_CONF_FILE=/home/vimkim/gh/cb/pr7925-01-stored-rows/.cub-workenv/conf/cubrid.conf
export CUBRID_BROKER_CONF_FILE=/home/vimkim/gh/cb/pr7925-01-stored-rows/.cub-workenv/conf/cubrid_broker.conf
export CUBRID_DATABASES=/home/vimkim/gh/cb/pr7925-01-stored-rows/.cub-workenv/databases
export CUBRID_TMP=/tmp/cwe-1000/b0aa9ef095a4
export CUBRID_CUBRID_PORT_ID=41038
export PATH=/home/vimkim/.cub/install/pr7925-01-stored-rows/debug_gcc/bin${PATH:+:$PATH}
export LD_LIBRARY_PATH=/home/vimkim/.cub/install/pr7925-01-stored-rows/debug_gcc/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export CUBRID_JAVA_HOME=/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8
export CUBRID_RUNTIME_READY=1
