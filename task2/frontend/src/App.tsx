import React,{useEffect,useMemo,useState} from "react"
import "./styles.css"
import { fetchJourney, fetchMembers, fetchMetrics } from "./api"
import { Episode, MemberJourney, InternalMetrics } from "./types"
import Timeline from "./components/Timeline"
import PersonaCard from "./components/PersonaCard"
import DecisionTrace from "./components/DecisionTrace"
import MetricsDashboard from "./components/MetricsDashboard"
import EpisodeDetails from "./components/EpisodeDetails"
import ChatAgent from "./components/ChatAgent"

export default function App(){
  const [members,setMembers]=useState<{id:number;name:string}[]>([])
  const [memberId,setMemberId]=useState<number|null>(null)
  const [journey,setJourney]=useState<MemberJourney|null>(null)
  const [metrics,setMetrics]=useState<InternalMetrics|null>(null)
  const [currentEpisodeId,setCurrentEpisodeId]=useState<number|undefined>(undefined)

  useEffect(()=>{(async()=>{
    const ms=await fetchMembers(); setMembers(ms); if(ms.length>0) setMemberId(ms[0].id)
  })()},[])

  useEffect(()=>{(async()=>{
    if(!memberId) return
    const j=await fetchJourney(memberId); setJourney(j); setCurrentEpisodeId(j.episodes[0]?.id)
    const m=await fetchMetrics(memberId); setMetrics(m)
  })()},[memberId])

  const currentEpisode:Episode|null = useMemo(()=>(
    !journey||currentEpisodeId===undefined ? null :
    (journey.episodes.find(e=>e.id===currentEpisodeId)??null)
  ),[journey,currentEpisodeId])

  return (
    <div className="container">
      {/* Branded header */}
      <div className="header">
        <div className="brand">
          <img src="/elyx-favicon.svg" alt="Elyx" className="logo"/>
          <div>
            <h1 className="title">Member Journey Visualization & Reasoning</h1>
            <div className="tagline">The Healthcare You Deserve</div>
          </div>
        </div>
        <div>
          <select className="btn" value={memberId??""} onChange={e=>setMemberId(Number(e.target.value))}>
            {members.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>
      </div>

      {journey&&(<>
        <div className="card"><h3>Member Journey Timeline</h3>
          <div className="timeline">
            {journey.episodes.map(e=>(
              <div key={e.id}
                   className={"dot "+(e.id===currentEpisodeId?"active":"")}
                   data-label={`${e.title}`}
                   onClick={()=>setCurrentEpisodeId(e.id)}
                   title={`${e.title} (${e.start_date} → ${e.end_date})`}/>
            ))}
          </div>
        </div>

        <div className="grid" style={{marginTop:16}}>
          <div>
            <EpisodeDetails ep={currentEpisode}/>
            {currentEpisode&&(<DecisionTrace decisions={currentEpisode.decisions} chats={journey.chats}/>)}
          </div>
          <div>
            {currentEpisode&&(<PersonaCard before={currentEpisode.persona_before} after={currentEpisode.persona_after}/>)}
            <ChatAgent memberId={journey.member_id}/>
          </div>
        </div>

        <div className="row">
          <div className="item" style={{gridColumn:"1 / span 2"}}>
            <MetricsDashboard metrics={metrics}/>
          </div>
        </div>
      </>)}
    </div>
  )
}