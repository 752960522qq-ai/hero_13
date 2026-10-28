// XPBD distance constraints adapted from gpu-cloth-sim (alien-life, MIT, 2026).
// Browser CPU implementation: no Godot RenderingDevice or compute shader required.
export class ClothPhysics {
 constructor({cols=20,rows=24,width=1.2,height=1.3,centerX=1.35,top=2.02,z=.22}={}){
  Object.assign(this,{cols,rows,width,height,centerX,top,z});this.count=(cols+1)*(rows+1);this.p=new Float32Array(this.count*3);this.prev=new Float32Array(this.p.length);this.rest=new Float32Array(this.p.length);this.mass=new Float32Array(this.count).fill(1);this.edges=[];this.wind=1;this.time=0;this.accum=0;this.paused=false;this.released=false;this.grab=-1;this.grabTarget=[0,0,0];this.spheres=[{x:centerX,y:.55,z:.22,r:.27}];this.capsules=[];
  for(let y=0;y<=rows;y++)for(let x=0;x<=cols;x++){let i=y*(cols+1)+x;this.rest.set([centerX-width/2+x*width/cols,top-y*height/rows,z],i*3);}
  const edge=(a,b,c)=>{let k=a*3,l=b*3;this.edges.push({a,b,rest:Math.hypot(this.rest[l]-this.rest[k],this.rest[l+1]-this.rest[k+1],this.rest[l+2]-this.rest[k+2]),c,lambda:0});};
  for(let y=0;y<=rows;y++)for(let x=0;x<=cols;x++){let i=y*(cols+1)+x;if(x<cols)edge(i,i+1,1e-8);if(y<rows)edge(i,i+cols+1,1e-8);if(x<cols&&y<rows){edge(i,i+cols+2,2e-7);edge(i+1,i+cols+1,2e-7);}if(x<cols-1)edge(i,i+2,8e-5);if(y<rows-1)edge(i,i+2*(cols+1),8e-5);}
  this.reset();
 }
 reset(){this.p.set(this.rest);this.prev.set(this.rest);this.mass.fill(1);this.mass[0]=this.mass[this.cols]=0;this.released=false;this.grab=-1;this.time=0;this.accum=0;}
 release(){this.released=true;this.mass[0]=this.mass[this.cols]=1;}
 startGrab(i,target){this.grab=i;this.grabMass=this.mass[i];this.mass[i]=0;this.moveGrab(target);}
 moveGrab(target){for(let k=0;k<3;k++)this.grabTarget[k]=target[k];if(this.grab>=0){this.p.set(this.grabTarget,this.grab*3);this.prev.set(this.grabTarget,this.grab*3);}}
 endGrab(){if(this.grab>=0)this.mass[this.grab]=this.released?1:this.grabMass;this.grab=-1;}
 update(dt){if(this.paused)return;this.accum+=Math.min(dt,.05);const h=1/120;let n=0;while(this.accum>=h&&n++<6){this.step(h);this.accum-=h;}}
 step(h){this.time+=h;const p=this.p,prev=this.prev,w=this.mass;const wind=this.wind*(1+.35*Math.sin(this.time*1.9));
  for(let i=0;i<this.count;i++){if(!w[i])continue;let k=i*3;for(let a=0;a<3;a++){let acceleration=a===1?-9.81:a===2?wind*(2.2+Math.sin(this.time*2+p[k]*2+p[k+1])):wind*.35*Math.sin(this.time+p[k+1]*3);let old=p[k+a];let v=(old-prev[k+a])*.996;v=Math.max(-.04,Math.min(.04,v));p[k+a]=old+v+acceleration*h*h;prev[k+a]=old;}}
  for(const e of this.edges)e.lambda=0;
  for(let it=0;it<6;it++){
   for(const e of this.edges){let a=e.a*3,b=e.b*3,wa=w[e.a],wb=w[e.b],sum=wa+wb;if(!sum)continue;let dx=p[b]-p[a],dy=p[b+1]-p[a+1],dz=p[b+2]-p[a+2],len=Math.hypot(dx,dy,dz);if(len<1e-8)continue;let alpha=e.c/(h*h),dl=(-(len-e.rest)-alpha*e.lambda)/(sum+alpha);e.lambda+=dl;let f=dl/len;p[a]-=wa*dx*f;p[a+1]-=wa*dy*f;p[a+2]-=wa*dz*f;p[b]+=wb*dx*f;p[b+1]+=wb*dy*f;p[b+2]+=wb*dz*f;}
   this.collide();if(this.grab>=0)this.moveGrab(this.grabTarget);
  }
 }
 collide(){const p=this.p;for(let i=0;i<this.count;i++){if(!this.mass[i])continue;let k=i*3;if(p[k+1]<.018){p[k+1]=.018;this.prev[k]+=(p[k]-this.prev[k])*.15;this.prev[k+2]+=(p[k+2]-this.prev[k+2])*.15;}
  for(const s of this.spheres)this.project(k,s.x,s.y,s.z,s.r+.012);
  for(const c of this.capsules){let ax=c.b[0]-c.a[0],ay=c.b[1]-c.a[1],az=c.b[2]-c.a[2],length=ax*ax+ay*ay+az*az;let t=length>1e-8?Math.max(0,Math.min(1,((p[k]-c.a[0])*ax+(p[k+1]-c.a[1])*ay+(p[k+2]-c.a[2])*az)/length)):0;this.project(k,c.a[0]+t*ax,c.a[1]+t*ay,c.a[2]+t*az,c.r+.012);}
 }}
 project(k,x,y,z,r){let p=this.p,dx=p[k]-x,dy=p[k+1]-y,dz=p[k+2]-z,d=Math.hypot(dx,dy,dz);if(d>=r)return;if(d<1e-8){dx=0;dy=0;dz=1;d=1;}let s=r/d;p[k]=x+dx*s;p[k+1]=y+dy*s;p[k+2]=z+dz*s;}
}
