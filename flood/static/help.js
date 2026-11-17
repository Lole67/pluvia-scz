'use strict';
(()=>{
 const panel=document.getElementById('help-panel');let opener;
 function topic(id){const target=document.getElementById(id);if(target){target.scrollIntoView({block:'start'});target.focus({preventScroll:true});}}
 document.querySelectorAll('[data-help]').forEach(button=>button.addEventListener('click',()=>{opener=button;panel.showModal();topic(button.dataset.help);}));
 document.querySelectorAll('[data-topic]').forEach(button=>button.addEventListener('click',()=>topic(button.dataset.topic)));
 document.getElementById('close-help').addEventListener('click',()=>panel.close());
 panel.addEventListener('close',()=>{if(opener)opener.focus();});
 panel.addEventListener('click',event=>{if(event.target===panel){const r=panel.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)panel.close();}});
})();
