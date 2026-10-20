const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();
function node(s){if(!elements.has(s))elements.set(s,{innerHTML:'',textContent:'',style:{},classList:{toggle(){}},open:false,showModal(){},close(){},value:''});return elements.get(s);}
const context={document:{querySelector:node,querySelectorAll:()=>[],addEventListener(){}},window:{addEventListener(){}},location:{hash:'#overview'},sessionStorage:{getItem(){return null;}},setInterval(){},clearInterval(){},setTimeout(){},fetch:()=>new Promise(()=>{}),console};
vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/studies.js','utf8'),context);
vm.runInContext(fs.readFileSync('frontend/app.js','utf8'),context);
const task={id:'g',version:'1',title:'Task',kind:'group',issues:[{id:'a',number:'1',title:'公开问题',summary:'独立 issue 题面摘要',body:'整理后的题面'}],readme:'# 任务说明\n\n公开 README 内容',budget:{wall_clock_minutes:150},required_output:['patch','report'],tags:[]};
const run={id:'r',task,agent:{name:'DSH',model:'deepseek-flash'},mode:'live',status:'failed',events:[],checks:[],artifacts:[],report:'report',experiment_id:'e',attempt:1,issue_reports:[{issue_id:'a',root_cause:'<script>unsafe</script>'}],submission_contract:{passed:true,errors:[]}};
const experiment={id:'e',title:'Batch',phase:'1A',status:'draft',agent:run.agent,repeats:2,request_limit:317,wall_seconds:1800,groups:[],task_snapshots:[task],gate:{},prompt_version:'v1'};
context.fixture={tasks:[task],runs:[run],agents:[],adapters:{},experiments:[experiment],evaluations:[],assets:[{id:'k',label:'K1',kind:'kernel',status:'candidate'}]};
vm.runInContext('state=fixture;',context);
for(const route of ['overview','tasks','task/g/1','agents','runs','run/r','compare','system','experiments','experiment/e','assets','asset/k']){
 context.location.hash='#'+route;vm.runInContext('render()',context);
 assert(node('#main').innerHTML.length>50,route+' empty');
 assert(!node('#main').innerHTML.includes('页面不存在'),route+' invalid');
 if(route==='experiment/e')assert(node('#main').innerHTML.includes('317 请求'),'custom budget invisible');
 if(route==='run/r'){assert(node('#main').innerHTML.includes('逐 issue 修复报告'));assert(!node('#main').innerHTML.includes('<script>unsafe'))}
 if(route==='task/g/1'){assert(node('#main').innerHTML.includes('任务 README'));assert(node('#main').innerHTML.includes('公开 README 内容'));assert(node('#main').innerHTML.includes('问题说明'))}
}
console.log('12 UI routes render; per-issue claims escaped; custom budget visible.');
