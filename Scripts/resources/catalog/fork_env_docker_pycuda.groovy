// This script creates a docker fork environment using pycuda (CPU + GPU configuration)

// In the Java Home location field, use the value: "/usr" to force using the JRE provided in the docker image below (Recommended).
// Be aware, that the prefix command is internally split by spaces. So paths with spaces won't work.
// Prepare Docker parameters

containerName = "activeeon/pycuda:latest"

dockerRunCommand =  "docker run "
dockerParameters = "--rm "
// Prepare ProActive home volume
paHomeHost = variables.get("PA_SCHEDULER_HOME")
paHomeContainer = variables.get("PA_SCHEDULER_HOME")
proActiveHomeVolume = "-v " + paHomeHost + ":" + paHomeContainer + " "
// Prepare working directory (For Dataspaces and serialized task file)
workspaceHost = localspace
workspaceContainer = localspace
workspaceVolume = "-v " + workspaceHost + ":" + workspaceContainer + " "
// Prepare container working directory
containerWorkingDirectory = "-w " + workspaceContainer + " "

deviceDirectories = "--device /dev/nvidia0:/dev/nvidia0 --device /dev/nvidiactl:/dev/nvidiactl --device /dev/nvidia-uvm:/dev/nvidia-uvm "

sigar = new org.hyperic.sigar.Sigar()
try {
    pid = sigar.getPid()
    creds = sigar.getProcCred(pid)
    uid = creds.getUid()
    gid = creds.getGid()
    userDefinition = "--user=" + uid + ":" + gid + " "
} catch (Exception e) {
    println "Cannot retrieve user or group id : " + e.getMessage()
    userDefinition = "";
} finally {
    sigar.close()
}

// Save pre execution command into magic variable 'preJavaHomeCmd', which is picked up by the node
preJavaHomeCmd = dockerRunCommand + dockerParameters + proActiveHomeVolume + workspaceVolume + userDefinition + containerWorkingDirectory + deviceDirectories + containerName
println "DOCKER_FULL_CMD:    " + preJavaHomeCmd

