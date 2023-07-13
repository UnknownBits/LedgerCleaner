import sqlite3, datetime, os, json, time
from mcdreforged.api.all import new_thread

is_getting_clean_info = False

def get_file_size(filePath):
    fsize = os.path.getsize(filePath)	# 返回的是字节大小
    if fsize < 1024:
        return "%.02fB"%fsize
    else: 
        KBX = fsize/1024
        if KBX < 1024:
            return "%.02fKB"%MBX
        else:
            MBX = KBX /1024
            if MBX < 1024:
                return "%.02fMB"%MBX
            else:
                return "%.02fGB"%(MBX/1024)

def run_command_text(string):
    return {"text":"§7%s§f"%string, "clickEvent":{"action":"run_command","value":string}, "hoverEvent":{"action":"show_text","value":{"text":"点击输入"}}}

def text(string):
    return {"text":string}

class SQLiteOperation:

    def __init__(self, server, sqlite_file, interval_days) -> None:
        self.server = server
        self.connected = False
        self.is_cleaning = False
        sqlite_file = os.getcwd()+sqlite_file
        if os.path.exists(sqlite_file):
            self.sqlite_file = sqlite_file
            self.interval_days = interval_days
            server.logger.info("ledger sqlite checked.")
        else:
            self.sqlite_file = None
            server.logger.warn("ledger sqlite not found: %s, cwd: %s"%(sqlite_file,os.getcwd()))
        
        self.help_message = [
            text("§e§l[Ledger Cleaner]\n"),
            run_command_text("!!ledger help"),text(" 显示此帮助\n"),
            run_command_text("!!ledger size"),text(" 获取数据库大小\n"),
            run_command_text("!!ledger connect"),text(" 连接到数据库\n"),
            run_command_text("!!ledger close"),text(" 断开数据库的连接\n"),
            run_command_text("!!ledger clean"),text(" 清理数据库\n"),
            run_command_text("!!ledger free"),text(" 释放空数据的硬盘空间(建议clean后使用)"),
        ]
    
    def size(self):
        if self.sqlite_file:
            self.server.say("§e[ledger]§f 数据库大小: §b%s"%get_file_size(self.sqlite_file))
        else:
            self.server.say("§e[ledger]§f §c未找到数据库文件")

    def help(self):
        self.server.execute("tellraw @a %s"%json.dumps(self.help_message))

    def connect(self, prompt=True, fresh_connect_time=True):
        if not self.connected:
            if self.sqlite_file:
                self.connected = True
                self.sqlite = sqlite3.connect(self.sqlite_file)
                if fresh_connect_time:
                    self.connect_time = datetime.datetime.now()
                if prompt:
                    self.server.say("§e[ledger]§f 数据库§a成功连接§f(§b%s§f)"%get_file_size(self.sqlite_file))
            else:
                self.server.say("§e[ledger]§f §c未找到数据库文件")
        elif prompt:
            self.server.say("§e[ledger]§f §a数据库已经连接了")
    
    def close(self, commit=True, vacuum=False, prompt=True):
        if self.connected:
            if commit:
                self.sqlite.commit()
            if vacuum:
                self.sqlite.execute("vacuum")
            self.sqlite.close()
            self.connected = False
            if prompt:
                self.server.say("§e[ledger]§f 数据库§c断开连接§f(§b%s§f)"%get_file_size(self.sqlite_file))
        else:
            self.server.say("§e[ledger]§f §c数据库未连接")
    
    # @new_thread("SQLite")
    def clean(self, date=None):
        global is_getting_clean_info
        if is_getting_clean_info:
            self.server.say("§c已有clean任务")
            return
            
        try:
            self.connect(prompt=False)
            if self.connected:
                is_getting_clean_info = True
                
                if date:
                    try:
                        split_date = datetime.datetime.strptime(date,"%Y-%m-%d")
                    except:
                        self.server.say("§c错误的日期格式: %s, 格式应为'年-月-日'"%date)
                        return
                else:
                    split_date = self.connect_time - datetime.timedelta(self.interval_days)
                self.server.say("§e[ledger]§f 准备§c清理§f日期§b%s§f前的所有Actions数据"%split_date.strftime("%Y-%m-%d %H:%M:%S"))
                
                cour = self.sqlite.cursor()
                min_id, max_id = cour.execute("select min(id) from actions").fetchone()[0],cour.execute("select max(id) from actions").fetchone()[0]
                start_id = min_id
                self.server.say("§e[ledger]§f 查询到§b%s§f条记录"%(max_id-min_id+1))
                total_count = max_id-min_id+1
                self.server.logger.info("查询到§b%s+§f条记录"%total_count)
                to_datetime = lambda string: datetime.datetime.strptime(string,"%Y-%m-%d %H:%M:%S.%f")
                search_times = 0
                action = cour.execute("select time from actions WHERE id = %s"%min_id).fetchone()[0]
                if to_datetime(action) < split_date:
                    while True:
                        search_times += 1
                        mid_id = int((min_id+max_id)/2)
                        action = cour.execute("select time from actions WHERE id = %s"%mid_id).fetchone()[0]
                        if to_datetime(action) < split_date:
                            action2 = cour.execute("select time from actions WHERE id = %s"%(mid_id+1)).fetchone()[0]
                            if to_datetime(action2) > split_date:
                                mid_id += 1
                                break
                            else:
                                min_id = mid_id
                        else:
                            max_id = mid_id
                    self.server.logger.info("二分查找%s次,id=%s"%(search_times,mid_id))
                else:
                    mid_id = min_id
                self.del_id = mid_id
                del_count = mid_id-start_id
                self.close(False,False,False)
                self.server.logger.info("数据库断开连接")
                is_getting_clean_info = False
            else:
                return
        except Exception:
            self.close()
            is_getting_clean_info = False
            raise Exception

        info = [{"text":"§e[ledger]§f 将清理§b%s§f条(§d%.02f%%§f)数据 "%(del_count, del_count/total_count*100)},
                {"text":"§7!!ledger clean confirm","clickEvent":{"action":"run_command","value":"!!ledger clean confirm"}},
                {"text":" 以§c确认"}]
        self.server.execute("tellraw @a %s"%json.dumps(info))

        self.is_cleaning = True
    
    @new_thread("ledger-clean")
    def clean_confirm(self):
        if self.is_cleaning:
            self.connect(prompt=False)
            try:
                if self.connected:
                    self.server.say("§e[ledger]§f 正在清理")
                    cour = self.sqlite.cursor()
                    sql = 'delete from actions where id < %s'%self.del_id
                    cour.execute(sql)
                    self.server.say("§e[ledger]§f 正在执行操作")
                    self.close(prompt=False)
                    self.server.say("§e[ledger]§f §a清理完成")
            except Exception as e:
                self.close(prompt=False)
                raise e
        else:
            self.server.say("§e[ledger]§f §c没有清理任务可以确认")
    
    @new_thread("ledger-free")
    def free(self):
        self.connect()
        if self.connected:
            s_time = time.time()
            self.server.say("§e[ledger]§f 准备释放空间")
            self.close(vacuum=True)
            self.server.say("§e[ledger]§f 释放完成，用时§b%.1fs"%(time.time()-s_time))
    

        