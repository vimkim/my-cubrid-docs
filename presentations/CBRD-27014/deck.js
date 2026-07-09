(function(){
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var total=slides.length, cur=0;
  var params=new URLSearchParams(location.search);
  var flat=params.has('flat');

  slides.forEach(function(s,i){
    var pg=s.querySelector('.pg'); if(pg) pg.textContent=(i+1)+' / '+total;
  });

  function show(n){
    cur=Math.max(0,Math.min(total-1,n));
    slides.forEach(function(s,i){s.classList.toggle('active',i===cur);});
    document.getElementById('pager').textContent=(cur+1)+' / '+total;
    if(!flat) location.hash=String(cur+1);
  }
  function fit(){
    if(flat) return;
    var sc=Math.min(innerWidth/1280,innerHeight/720);
    document.getElementById('frame').style.transform='scale('+sc+')';
  }

  if(flat){
    document.body.classList.add('flat');
    var n=parseInt(params.get('slide')||'1',10)-1;
    show(isNaN(n)?0:n);
  }else{
    var h=parseInt((location.hash||'').replace('#',''),10);
    show(isNaN(h)?0:h-1);
    fit();
    addEventListener('resize',fit);
    addEventListener('keydown',function(e){
      if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown') show(cur+1);
      else if(e.key==='ArrowLeft'||e.key==='PageUp') show(cur-1);
      else if(e.key==='Home') show(0);
      else if(e.key==='End') show(total-1);
    });
    addEventListener('click',function(e){
      if(e.target.closest('a')) return;
      show(e.clientX>innerWidth/2?cur+1:cur-1);
    });
  }
})();
