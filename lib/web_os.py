# MIT License
#
# Copyright (c) 2022  Dr. Magnus Christ (mc0110)
#
# This is part of the wifimanager package
# 
# 
from machine import soft_reset, reset
from gen_html import Gen_Html
from nanoweb import HttpError, Nanoweb, send_file
import uasyncio as asyncio
import gc

naw = Nanoweb(100)

def init(w, n):
    global gh
    global reboot
    global soft_reboot
    global repo_update
    global repo_success
    global repo_update_comment
    global naw
    naw = n
    gc.enable()
    gh = Gen_Html(w)
    reboot = False
    soft_reboot = False
    repo_update = False
    repo_update_comment = ""
    repo_success = False


def unquote(s):
    if '%' not in s:
        return s
    s = s.split("%")
    a = s[0].encode("utf-8")
    for i in s[1:]:
        a = a + bytearray.fromhex(i[:2]) + i[2:].encode("utf-8")
    return a.decode("utf-8")    


async def command_loop():
    global reboot
    global soft_reboot
    global repo_update
    global repo_update_comment
    global repo_success
    while True:
        await asyncio.sleep(3) # Update every 10sec
        if reboot:
            await asyncio.sleep(10) # Update every 10sec
            reset()
        if soft_reboot:
            await asyncio.sleep(10) # Update every 10sec
            soft_reset()
        if repo_update:
            await asyncio.sleep(10) # Update every 10sec
            if not(repo_update): return
            import cred
            rel_new = cred.read_repo_rel()
            repo_update_comment = " update to rel: " + rel_new
            repo_success = True
            if (rel_new != gh.wifi.rel_no):
                repo_update_comment = " update to rel: " + rel_new
                await asyncio.sleep(5) # sleep for 5s to send it to browser
                # loop for update-process
                for i, st in cred.update_repo():
                    print(i, st)
                    repo_success = repo_success and st
                    if st:
                        repo_update_comment = i + " loaded"
                    else:
                        repo_update_comment = i + " not successful"    
                    await asyncio.sleep(5) # sleep for 500ms
                # gh.refresh_connect_state()
            else: # no update neccesary   
                repo_update_comment = "repo up to date"
                await asyncio.sleep(5) # sleep
            repo_update = False
        gh.wifi.set_led(2)
        

# Declare route directly with decorator
@naw.route('/')
async def index(r):
    global gh
    global repo_update
    repo_update = False
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleRoot())
    
@naw.route('/s')
async def status(r):
    global gh
    global repo_update
    # gh.refresh_connect_state()
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleStatus("Device status", "/", "Back",("30","/")))

@naw.route('/loop')    
async def loop(r):
    global repo_update_comment
    global repo_update
    global repo_success
    
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    if repo_update:
        await r.write(gh.handleMessage("Update is running -> " + repo_update_comment, "/", "Back",("3","/loop")))
    else:
        if repo_success:        
            await r.write(gh.handleMessage("Update finalized successful, pls reboot device now", "/", "Back",("5","/")))
        else:    
            await r.write(gh.handleMessage("Update finalized unsuccessful, pls repeat update", "/", "Back",("5","/")))
        
    
@naw.route('/ta')    
async def toggle_ap(r):
    global gh
    if not(gh.wifi.set_sta()):
        await r.write("HTTP/1.1 200 OK\r\n\r\n")
        await r.write(gh.handleMessage("You couldn't release both (AP, STA), then you loose the connection to the port", "/", "Back",("2","/")))
    else:
        gh.wifi.set_ap(not(gh.wifi.set_ap()))
        await r.write("HTTP/1.1 200 OK\r\n\r\n")
        await r.write(gh.handleRoot())

@naw.route('/ts1')
async def set_sta(r):
    global gh
    a = gh.wifi.set_sta(1)
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    if a:
        await r.write(gh.handleMessage("STA-connection established successfull", "/", "Cancel",("5","/")))
    else:
        await r.write(gh.handleMessage("Couldn't establish a STA-connection", "/", "Cancel",("5","/")))

@naw.route('/ts')
async def toggle_sta(r):
    global gh
    if not(gh.wifi.set_ap()):
        await r.write("HTTP/1.1 200 OK\r\n\r\n")
        await r.write(gh.handleMessage("You couldn't release both (AP, STA), then you loose the connection to the port", "/", "Back",("5","/")))
    else:
        await r.write("HTTP/1.1 200 OK\r\n\r\n")
        if not(gh.wifi.set_sta()):
            await r.write(gh.handleMessage("Try to establish a STA-connection", "/", "Cancel",("5","/ts1")))
        else:    
            gh.wifi.set_sta(0)
            await r.write(gh.handleMessage("STA connection deactivated", "/", "Back",("5","/")))
        
@naw.route('/rm')
async def toggle_run_mode(r):
    global gh
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    if not(gh.wifi.creds()):
        await r.write(gh.handleMessage("You couldn't switch run-mode without credentials", "/", "Back",("5","/")))
    else:
        a = gh.wifi.run_mode()
        if a < 2: a += 1
        else: a=0    
        gh.wifi.run_mode(a)
        await r.write(gh.handleMessage("RUN mode changed", "/", "Back",("5","/")))

@naw.route('/wc')
# Generate the credential form    
async def creds(r):
    global gh
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await send_file(r, gh.handleCredentials(gh.JSON))


@naw.route('/scan')
async def scan_networks(r):
    global gh
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    if gh.wifi.set_sta():
        await r.write(gh.handleScan_Networks())
    else:    
        await r.write(gh.handleMessage("This needs STA-mode", "/wc", "Back",("5","/wc")))

@naw.route('/cp')
async def cp(r):
    global gh
    json = {}
    # convert JSON to json_result = {key: value}
    for i in gh.JSON.keys():        
        json[i] = "0"       
    for i in r.args.keys():
        if r.args[i]=="True":
            json[i] = "1"
        else:
            json[i] = unquote(r.args[i])
    gh.wifi.store_creds(json)
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleMessage("Credentials are written", "/", "Back",("5","/")))


@naw.route('/dc')
async def del_cred(r):
    global gh
    gh.wifi.delete_creds()
    print("Credentials moved to bak")
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleMessage("Credentials are deleted", "/", "Back",("5","/wc")))


@naw.route('/sc')
async def swp_cred(r):
    global gh
    gh.wifi.swap_creds()
    print("Credentials swapped")
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleMessage("Credentials are swapped", "/", "Back",("5","/wc")))
    
@naw.route('/rc')
async def res_cred(r):
    global gh
    gh.wifi.restore_creds()
    print("Credentials restored")
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleMessage("Credentials are restored", "/", "Back",("5","/")))
    
@naw.route('/ur')
async def ur(r):
    global gh
    if gh.wifi.set_sta():
        await r.write("HTTP/1.1 200 OK\r\n\r\n")
        await r.write(gh.handleMessage("For repo-update press 'UPDATE'", "/ur1", "UPDATE",("5","/")))
    else:
        await r.write("HTTP/1.1 200 OK\r\n\r\n")
        await r.write(gh.handleMessage("You need a STA-internet-connection", "/", "Back",("5","/")))

@naw.route('/ur1')
async def ur1(r):
    global gh
    global repo_update
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    print("Repo update starting ...")
    repo_update = True
    await r.write(gh.handleMessage("Repo update initiated", "/", "Back",("5","/loop")))

@naw.route('/rb')
async def s_reboot(r):
    global soft_reboot
    soft_reboot = True
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleMessage("Device will be soft rebooted", "/", "Continue",("4","/")))

@naw.route('/rb1')
async def h_reboot(r):
    global reboot
    reboot = True
    await r.write("HTTP/1.1 200 OK\r\n\r\n")
    await r.write(gh.handleMessage("Device will be hard rebooted", "/", "Continue",("4","/")))

@naw.route('/upload')
async def upload(r):
    global gh
    dir = r.url[7:]
    if dir == "__":
        dir = "/"
    else:
        dir = "/" + dir.strip("/") + "/"    
    if r.method == "POST":
        # obtain the filename and size from request headers
        filename = r.headers['Content-Disposition'].split('filename=')[1].strip('"')
        size = int(r.headers['Content-Length'])
        # sanitize the filename
        # write the file to the files directory in 1K chunks
        with open(dir + filename, 'wb') as f:
            while size > 0:
                chunk = await r.read(min(size, 1024))
                f.write(chunk)
                size -= len(chunk)
            f.close()        
        print('Successfully saved file: ' + dir + filename)
        await r.write("HTTP/1.1 201 Upload \r\n" )
        await send_file(r, gh.handleFiles(dir))
    else:
        await r.write("HTTP/1.1 200 OK\r\n")
        await send_file(r, gh.handleFiles(dir))

@naw.route('/fm*')
async def fm(r):
    global gh
    filename = r.param["fn"]
    direct = r.param["dir"]

    if r.param["button"]=="Delete":
        print("delete file: " + direct+filename)
        try:
            os.remove(direct+filename)
        except OSError as e:
            raise HttpError(r, 500, "Internal error")
        rp = gh.handleFiles(direct)
        await r.write("HTTP/1.1 200 OK\r\n")
        await send_file(r, rp)
    elif r.param["button"]=="Download":
        print("download file: " + filename)
        await r.write("HTTP/1.1 200 OK\r\n") 
        await r.write("Content-Type: application/octet-stream\r\n")
        await r.write("Content-Disposition: attachment; filename=%s\r\n\r\n" % filename)
        await send_file(r, direct+filename)


@naw.route('/dir*')
async def set_dir(r):
    global gh
    new_dir = r.url[5:]
    if new_dir.startswith("__"):
        await r.write("HTTP/1.1 200 OK\r\n")
        await send_file(r, gh.handleFiles("/"))
    else:
        await r.write("HTTP/1.1 200 OK\r\n")
        await send_file(r, gh.handleFiles(new_dir))

