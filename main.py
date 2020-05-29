from IPython.display import display, Markdown
import time
import math
import random
import sys
from math import ceil

JOBS_NUM = 4
MAX_TASKS = 4
MIN_TASKS = 2
TASKS_NUM = 13
MACHINES_NUM = 4
number = 1
CONFLICT_HASH_WEIGHT = 100

# -------------------------------------------------------------------
# problem generation
CONFLICT_HASH_WEIGHT = 100

def nextIdx(idx):
    idx = idx + 1
    if idx == JOBS_NUM:
        idx = 0
    return idx


def chooseNumberOfTasks(nums):
    too_few = [x for x in nums if x < MIN_TASKS]
    idx = random.randint(0, JOBS_NUM - 1)
    if len(too_few) > 0:
        while nums[idx] >= MIN_TASKS:
            idx = nextIdx(idx)
    while nums[idx] == MAX_TASKS:
        idx = nextIdx(idx)
    return idx


def randomTime():
    rk = random.randint(1, 7)
    if rk == 7:
        return 4
    else:
        return int(math.floor((rk + 1) / 2))


def randomRoute(times):
    r = list(range(1, MACHINES_NUM + 1))
    random.shuffle(r)
    return r[:len(times)]


def generate():
    # distrubution of tasks
    nums = [0 for _ in range(JOBS_NUM)]
    for j in range(TASKS_NUM):
        idx = chooseNumberOfTasks(nums)
        nums[idx] = nums[idx] + 1

    # the jobs
    jobs = []
    for j in range(JOBS_NUM):
        t = [randomTime() for _ in range(nums[j])]
        m = randomRoute(t)
        jobs.append((0, t, m))

    # ready times
    rts = list(range(0, JOBS_NUM))
    random.shuffle(rts)
    _, t1, m1 = jobs[rts[0]]
    _, t2, m2 = jobs[rts[1]]
    jobs[rts[0]] = (1, t1, m1)
    jobs[rts[1]] = (2, t2, m2)

    return jobs

# -------------------------------------------------------------------
# problem solution

def getGreatest(lst):
    lst.sort(key=lambda x: x[1])
    j = lst[-1][0]
    time = lst[-1][3]
    return (j, time)


def getLowest(lst):
    lst.sort(key=lambda x: x[1])
    j = lst[0][0]
    time = lst[0][3]
    return (j, time)


def resolveConflict(stacked_jobs, problem, next_task_number, method):
    if method == 'lpt':
        lst = []
        for j, time in stacked_jobs:
            proc_times = problem[j - 1][1]
            t = next_task_number[j - 1]
            p_time = proc_times[t - 1]
            lst.append((j, p_time * CONFLICT_HASH_WEIGHT - j, p_time, time))
        return getGreatest(lst)

    elif method == 'spt':
        lst = []
        for j, time in stacked_jobs:
            proc_times = problem[j - 1][1]
            t = next_task_number[j - 1]
            p_time = proc_times[t - 1]
            lst.append((j, p_time * CONFLICT_HASH_WEIGHT + j, p_time, time))
        return getLowest(lst)

    elif method == 'fifo':
        lst = []
        for j, time in stacked_jobs:
            lst.append((j, time * CONFLICT_HASH_WEIGHT + j, time, time))
        return getLowest(lst)

    elif method == 'lifo':
        lst = []
        for j, time in stacked_jobs:
            lst.append((j, time * CONFLICT_HASH_WEIGHT - j, time, time))
        return getGreatest(lst)

    elif method == 'edd':
        lst = []
        for j, time in stacked_jobs:
            proc_times = problem[j - 1][1]
            r_time = problem[j - 1][0]
            ddate = r_time + sum(proc_times)
            lst.append((j, ddate * CONFLICT_HASH_WEIGHT + j, ddate, time))
        return getLowest(lst)

    elif method == 'lwr':
        lst = []
        for j, time in stacked_jobs:
            proc_times = problem[j - 1][1]
            t = next_task_number[j - 1]
            remaining_time = sum(proc_times[(t - 1):])
            lst.append((j, remaining_time * CONFLICT_HASH_WEIGHT + j, remaining_time, time))
        return getLowest(lst)


def scheduleTask(j, t, m, s_time, p, schedule):
    _, times, _ = p[j - 1]
    processing_time = times[t - 1]
    c_time = s_time + processing_time
    schedule.append((j, t, m, s_time, c_time))


def nextTimeMoment(time, p, schedule):
    next_times = []

    # get all the incoming job arrivals
    arrivals = [x[0] for x in p if x[0] > time]
    if len(arrivals) > 0:
        next_times.append(min(arrivals))

    # get all the incoming tasks completions
    completions = [x[4] for x in schedule if x[4] > time]
    if len(completions) > 0:
        next_times.append(min(completions))

    if len(next_times) > 0:
        return min(next_times)
    else:
        return -1


def machineBusy(m, time, schedule):
    tasks = [x for x in schedule if x[2] == m and x[3] <= time and x[4] > time]
    return len(tasks) > 0


# scheduled task: (job_number, task_number, machine_number, start, complete)
def solve(p, method):
    problem = list(zip(list(range(1, JOBS_NUM + 1)), p))
    schedule, time, conflicts, j_arrivals = [], 0, [], []
    stack = [[] for _ in range(MACHINES_NUM)]
    next_task_number = [1 for _ in range(JOBS_NUM)]

    while len(schedule) < TASKS_NUM:
        # handle all the jobs arrivals
        arrivals = [(j, info) for (j, info) in problem if info[0] == time]
        for (j, info) in arrivals:
            _, _, route = info
            # add the job to the machines stack
            stack[route[0] - 1].append((j, time))
            j_arrivals.append((j, route[0], time))

        # move completed jobs to next machines, when needed
        completions = [x for x in schedule if x[4] == time]
        for c_task in completions:
            j, t, _, _, _ = c_task
            _, _, route = p[j - 1]
            # was it the last task in the job?
            if len(route) == t:
                continue
            next_machine = route[t]
            stack[next_machine - 1].append((j, time))
            j_arrivals.append((j, next_machine, time))

        # handle the machines stacks
        handled_machines = []
        for (m, s) in zip(list(range(1, MACHINES_NUM + 1)), stack):
            if machineBusy(m, time, schedule):
                continue
            if len(s) == 0:  # no tasks to process
                continue
            if len(s) == 1:  # only one task to process, no conflict
                j, _ = s[0]
                t = next_task_number[j - 1]
                scheduleTask(j, t, m, time, p, schedule)
                next_task_number[j - 1] = t + 1
                handled_machines.append((m, s[0]))
            else:  # many tasks to process, a conflict to resolve
                j, at = resolveConflict(s, p, next_task_number, method)
                conflicts.append((time, m, s[:], j))
                t = next_task_number[j - 1]
                scheduleTask(j, t, m, time, p, schedule)
                next_task_number[j - 1] = t + 1
                handled_machines.append((m, (j, at)))

        # remove the handled jobs from the stacks
        for (m, to_remove) in handled_machines:
            stack[m - 1].remove(to_remove)

        time = nextTimeMoment(time, p, schedule)
        if time == -1:
            print("Something went wrong.")
            sys.exit(-1)

    return schedule, conflicts, j_arrivals


def stats(schedule, problem):
    cs, fs = [], []
    # get the ready times
    rs = [x[0] for x in problem]
    # get the completion times and calculate the flow times
    for j in range(1, JOBS_NUM + 1):
        csj = [x[4] for x in schedule if x[0] == j]
        cs.append(max(csj))
        fs.append(cs[j - 1] - rs[j - 1])
    cmax = max(cs)
    fmean = sum(fs) / float(JOBS_NUM)
    return (cmax, fmean)


def solution(p, method):
    print('% ' + method)
    s, c, a = solve(p, method)
    printSchedule(s)
    printConflicts(c)
    objectives = stats(s, p)
    print('%% cmax = %d, fmean = %f' % objectives)
    print('')
    return s, c, a

#Print schedule-------------------------------------------------------------------------------------------------------------------
def printMachine(num, schedule):
    tasks = [x for x in schedule if x[2] == num]
    tasks.sort(key=lambda x: x[3])
    strs = [str((x[0], x[3], x[4])) for x in tasks]
    comment('M' + str(num) + ' ' + ' '.join(strs))


def printSchedule(schedule):
    for i in range(1, MACHINES_NUM + 1):
        printMachine(i, schedule)

def printConflicts(cs):
    for c in cs:
        time, machine, j_infos, winner = c
        jobs = [j[0] for j in j_infos]
        comment(
            "Conflict: time " + str(time) + ", machine " + str(machine) + ", jobs: " + str(jobs) + ", winner: " + str(
                winner))
def comment(msg):
    print(("%% %s" % (msg,)))



#Create HTML table-------------------------------------------------------------------------------------------------------------------
#insert entities into html template 
def html_table(lol):
    i = 1
    markdownString = ''
    
    markdownString += '<table>'
    markdownString += '  <tr><td>'
    markdownString += '    </td><td> Task'
    markdownString += '    </td><td> Arrival Time'
    markdownString += '    </td><td> Task schedule'
    markdownString += '  </td></tr>'
    for sublist in lol:
        markdownString += '  <tr><td>'
        markdownString += '    </td><td>' + str(i)
        for item in sublist:
            markdownString += '    </td><td>' + item
        markdownString += '  </td></tr>'
        i += 1
    markdownString += '</table>'
    return markdownString

#split data from int list to raw string
def toHTMLlist(plist):
    htmlStr = []
    sizeList = ['1']
    for sublist1 in plist:
        for sublist2 in sublist1:
            if type(sublist2) == type(1):
                htmlStr.append(str(sublist2))
                sizeList.pop(len(sizeList)-1)
                continue
            sizeList.append(len(sublist2))
            for item in sublist2:
                htmlStr.append(str(item))
    sizeList.pop(len(sizeList) - 1)
    return htmlStr, sizeList

#create HTML entities to display
def formatHTMLstr(pHTML, sizeHTML):
    HTMLformat = []
    buildStr = []
    ite = 0
    for i in range(0, len(sizeHTML)):
        for j in range(ite, int(sizeHTML[i])+ 1 + ite):
            if j == ite:
                buildStr.append(pHTML[j])
            else:
                buildStr.append("M%s(%s)"%(pHTML[j+sizeHTML[i]],pHTML[j]))
        ite = ite + 2*sizeHTML[i] + 1
        HTMLformat.append(buildStr[:])
        buildStr.clear()
    return HTMLformat
def drawTable(p):
    pHTML, sizeLst = toHTMLlist(p)
    display(Markdown("# Schedule table for tasks"))
    display(Markdown(html_table(formatHTMLstr(pHTML, sizeLst))))

#User input ----------------------------------------------------------------------------------------------------------
def userInput():
    lines = []
    outNumberList = []
    intSplit = []
    outNumberTupla = ()
    returnList =[]

    display(Markdown("# Your Input"))
    time.sleep(0.1)
    while True:
        line = input()
        if line:
            line = line.split("|")
            for item in line:
                 item = item.replace(",", "").strip().split(" ")
                 for number in item:
                     intSplit.append(int(math.floor(float(number[:]))))
                 outNumberList.append(intSplit[:])
                 intSplit.clear()
            outNumberList[0] = int(outNumberList[0][0])
            OutNumberTupla = tuple(outNumberList)
            returnList.append(OutNumberTupla)
            outNumberList.clear()
        else:
            break
    return returnList

#Solve functions --------------------------------------------------------------------------------------------------------------
def userSolve():
    userp = userInput()
    drawTable(userp)
    schedule, conflicts, arrival_route = solution(userp, 'lpt')
    print("Schedule: \n",schedule)
    print("Conflicts: \n",conflicts)
    print("Arrival_route: \n",arrival_route)
    
def randomSolve():
    #number = int(input("input int seed for random data generation: "))
    random.seed(1) #number)
    p = generate()
   # drawTable(p)
    print(p)
    schedule, conflicts, arrival_route = solution(p, 'lpt')
    objectives = stats(schedule, p)
    drawGantt(schedule,conflicts,arrival_route,objectives[0])
    
#Gantt connector function -----------------------------------------------------------------------------------------------------
def tag(name, **kwargs):
    lst = ['<', name, ' ']
    for key in kwargs:
        lst.append( str(key) )
        lst.append( '="' )
        lst.append( str( kwargs[key] ) )
        lst.append( '" ' )
    lst.append('>')
    return ''.join(lst)

def tag2(name, **kwargs): #potrzebny do tego aby na była taka struktura < tekst tekst /> (w normalnym jest < tekst >
    lst = ['<', name, ' ']
    for key in kwargs:
        lst.append( str(key) )
        lst.append( '="' )
        lst.append( str( kwargs[key] ) )
        lst.append( '" ' )
    lst.append('/>')
    return ''.join(lst)

def path(d, stroke = 'black', fill = 'black', dots = False):
    if dots == False:
        return tag('path', d = d, stroke = stroke, fill = fill)
    else:
        return tag('path marker-start="url(#dot)" marker-mid="url(#dot)" marker-end="url(#dot)"', d = d, stroke = stroke, fill = fill)

def text(x, y, tekst, dx = 0, fill = 'black', dominant = 'middle', text_an = 'middle', font = 20):
    pom = 'text dominant-baseline = "'+dominant+'" text-anchor= "'+text_an+'" font-size ="'+str(font)+'"'
    lst = [tag(pom, x=x, y=y, dx=dx, fill=fill)]
    lst.append(tekst)
    lst.append(tag('/text'))
    return ''.join(lst)

def axis(nr_maszyny, cmax, delta):
    pos = nr_maszyny*20
    pos_str = str(pos)+'%'
    lst = [tag('svg', x=10,y=pos_str)]
    lst.append(tag('svg', x=20))
    lst.append('<defs>')
    lst.append('<marker id="dot" viewBox="0 0 10 10" refX="5" refY="5"')
    lst.append('markerWidth="5" markerHeight="5">')
    lst.append('<circle cx="5" cy="5" r="5" fill="black" />')
    lst.append('</marker>')
    lst.append('</defs>')
    pom = 'M 0,10 '
    x = round(cmax/delta)
    for i in range(1,x+1):
        pom = pom + 'h '+str(750/(cmax/delta)) + ' '
    pom = pom + 'z'
    #print(pom)
    lst.append(path(pom, dots = True))
    lst.append(tag('/svg'))
    lst.append(tag('svg'))
    lst.append(path('M 0,10 h 800 L 780,0 v 20 L 800,10 z'))
    lst.append(tag('/svg'))
    lst.append(text(x=815, y=10, tekst='t'))
    lst.append(text(x=20,y=25, tekst='0', font=''))
    for i in range(1,cmax+1):
        lst.append(text(x=20,y=25, dx=(i*750/(cmax/delta)), tekst=str(i*delta), font=''))
    lst.append(tag('</svg>'))
    lst.append(tag('<svg>'))
    lst.append(text(x=15, y=(str(pos-1.5)+'%'), tekst=('M'+str(nr_maszyny))))
    lst.append(tag('</svg>'))
    return ''.join(lst)

def ellipse(cx, cy, rx, ry, stroke='black', stroke_w=1, fill='white'):
    pom = 'ellipse stroke_width="'+str(stroke_w)+'"'
    return tag2(pom, cx=cx, cy=cy, rx=rx, ry=ry, stroke=stroke, fill=fill)

def ellipse_txt(radius, nr, duration, delta): #circle with txt
    rx = radius
    font = 30
    if(duration/delta < 1):
        rx = radius*(duration/delta)
        if(nr > 9):
            font = font*(duration/delta)+5
    lst = [ellipse(cx='50%', cy='50%', rx=rx, ry=radius)]
    lst.append(text(x='50%', y='55%', tekst=str(nr), font=font))
    return ''.join(lst)

def rectangle(width, height=50):
    return tag2('rect style="fill:white;stroke-width:2;stroke:black"', height=height, width=width)

def drawTask(nr,nr_maszyny, time,duration, cmax, delta): #powinno być task
    x_pos = 30+time*750/(cmax)
    y_pos = nr_maszyny*20 - 6.5
    y_pos_str = str(y_pos)+'%'
    lst = [tag('svg',x=x_pos,y=y_pos_str,height=50,width=str(duration * 750/(cmax)))]
    lst.append(rectangle(width=(duration * 750/(cmax))))
    lst.append(ellipse_txt(20, nr, duration, delta))
    lst.append('</svg>')
    return ''.join(lst)

def arrival(time, nr_maszyny, cmax, delta, *nr):
    el_pos_x = 30 + time * 750/(cmax)
    el_pos_y = nr_maszyny*20 - 11
    lst = [ellipse(cx=el_pos_x, cy=str(el_pos_y)+'%', rx=10*len(nr), ry=10)]
    i=0
    pom=''
    for key in nr:
        pom = pom + str(nr[i])
        i=i+1
        if(i!=len(nr)):
            pom = pom + ','
    lst.append(text(x=el_pos_x, y=str(el_pos_y + 0.5) + '%', tekst = pom))
    lst.append(tag('svg', x=el_pos_x-5, y=str(el_pos_y+1.5)+'%'))
    lst.append(path('M 5,0 v 20 L 0,10 h 10 L 5,20 z'))
    lst.append(tag('/svg'))
    return ''.join(lst)
def exit(time, cmax, delta, *nr):
    el_pos_x = 30 + time * 750/(cmax)
    lst = [ellipse(cx=el_pos_x, cy='93%', rx=10*len(nr), ry=10)]
    pom = ''
    i=0
    for key in nr:
        pom = pom + str(nr[i])
        i=i+1
        if(i!=len(nr)):
            pom = pom + ','
    lst.append(text(x = el_pos_x, y = '93.5%', tekst = pom))
    lst.append(tag('svg', x = el_pos_x-5, y = '87%'))
    lst.append(path('M 5,0 v 26 L 0,16 h 10 L 5,26 z'))
    lst.append(tag('/svg'))
    return ''.join(lst)
def conflict(time, nr_maszyny, cmax, delta): #czas i numer maszyny
    x_pos = 30 + time*750/(cmax)
    y_pos_str = str(nr_maszyny*20 - 6.5) + '%'
    lst = [tag('svg', x=x_pos, y=y_pos_str)]#za x trzeba dobry czas podstawic
    lst.append(tag('line',x1=0,y1=0,x2=0,y2=50,style="stroke:red;stroke-width:8"))
    lst.append(tag('/svg'))
    return ''.join(lst)

#gantt connector function -------------------------------------------------------------------------------------------

def drawGantt(sch,conf,arr,Cmax):
   # Cmax = 19    #trzeba wyznaczyc!!!!!!
    delta = ceil(Cmax/15) #to zostaw!!!!!
    Cmax = ceil(Cmax / delta) * delta #to zostaw!!!!!
    print(tag('svg', height=600, width=830))
    #change to gantt functions format
    changeFormat = []
    skipList = []
    br =0;
    #print(arr)
    for i in range(len(arr)): 
        for j in range(len(arr)):
            if(arr[i][1] == arr[j][1] and arr[i][2] == arr[j][2] and i != j):
                skipList.append([arr[i][0],arr[j][0],arr[i][2]])
   
    for i in range(int(len(skipList))):
        if(i%2 == 0):
            skipList.pop(i)
   # print(skipList)
    for item in arr:
        for i in range(len(skipList)+1):
            if(i != len(skipList)):
                if((item[0] == skipList[i][0] or item[0] == skipList[i][1]) and item[2] == skipList[i][2]):
                    changeFormat.append([item[2],item[1],Cmax,skipList[i][0],skipList[i][1]])
                    break;
            else:
                changeFormat.append([item[2],item[1],Cmax,item[0]])
                
        
    #print(changeFormat)
    
    #print arrivals cirlce
    for entity in changeFormat:
        if (len(entity) == 4):
            print(arrival(entity[0],entity[1],Cmax,delta,entity[3]))
        else:
            print(arrival(entity[0],entity[1],Cmax,delta,entity[3], entity[4]))
    
    #print rectancle tasks
    for task in sch:
        print(drawTask(task[0],task[2],task[3],task[4]-task[3],Cmax,delta))
              
    #print axies  need to implement finding exits points          
    for i in range(MACHINES_NUM):
       print(axis(i+1,Cmax,delta))
    
    
    #find exits
    sortSch = sch[:]
    sortSch.sort(key=lambda x: x[0]) #sort by task number     
    i = 1   
    max = 0
    maxList = []
    for item in sortSch:
        if(item[0] == i):
              max = item[4]
        else:
              maxList.append(max)
              i = i + 1
              max = item[4]
    maxList.append(max)
    
    exits = []    
    for i in range(len(maxList)):
        for j in range(len(maxList) - i):
            if(maxList[i] == maxList[j] and i != j):
                exits.append([maxList[i],Cmax,(i+1,j+1)])
            
        exits.append([maxList[i],Cmax,i+1])
        #print("==========================================================")
        #print(exits)
    #exits 
    for i in range(len(exits)):
        if(type(exits[i][2]) == type(1)):
            print(exit(exits[i][0],Cmax,delta,exits[i][2]))
        if(type(exits[i][2]) == type([1,2])):
            print(exit(exits[i][0],Cmax,delta,exits[i][2][0], exits[i][2][1]))
              
    for i in range((len(conf))):
        print(conflict(conf[i][0],conf[i][1],Cmax,delta))
    
    print(tag('/svg'))
    
    
    
#Example display -------------------------------------------------------------------------------------------------------------------------
def displayExample():
    display(Markdown("# Input data structure:"))
    display(Markdown("init task time| process time for each machine| Patch for task"))
    display(Markdown("# Input data example:"))
    display(Markdown("1| 1, 1, 3, 1| 3, 1, 2, 4"))
    display(Markdown("0| 2, 3, 2, 2| 1, 2, 3, 4"))
    display(Markdown("0| 1, 3, 1| 2, 3, 4"))
    display(Markdown("2| 2, 4| 3, 3"))
    p =  [(1, [1, 1, 3, 1], [3, 1, 2, 4]), (0, [2, 3, 2, 2], [1, 2, 3, 4]), (0, [1, 3, 1], [2, 3, 4]), (2, [2, 4], [3, 3])] #generate()
    pHTML, sizeLst = toHTMLlist(p)
    display(Markdown("# Schedule table for tasks"))
    display(Markdown(html_table(formatHTMLstr(pHTML, sizeLst))))

#main -------------------------------------------------------------------------------------------------------------------------

#displayExample()
#userSolve()
randomSolve()