import React, { useRef, useState, useEffect } from 'react'
import axios from 'axios'

const VideoEditor = ({ token }) => {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const timelineRef = useRef(null)

  const [videoFile, setVideoFile] = useState(null)
  const [videoUrl, setVideoUrl] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [clips, setClips] = useState([])
  const [selectedClip, setSelectedClip] = useState(null)
  const [effects, setEffects] = useState([])
  const [currentEffect, setCurrentEffect] = useState('none')
  const [projects, setProjects] = useState([])
  const [currentProject, setCurrentProject] = useState('Untitled Video Project')
  const [aiPrompt, setAiPrompt] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  const effectTypes = [
    { id: 'none', name: 'No Effect' },
    { id: 'grayscale', name: 'Grayscale' },
    { id: 'sepia', name: 'Sepia' },
    { id: 'blur', name: 'Blur' },
    { id: 'brightness', name: 'Brightness' },
    { id: 'contrast', name: 'Contrast' },
    { id: 'saturation', name: 'Saturation' },
    { id: 'hue-rotate', name: 'Hue Rotate' }
  ]

  const transitionTypes = [
    { id: 'none', name: 'No Transition' },
    { id: 'fade', name: 'Fade' },
    { id: 'wipe', name: 'Wipe' },
    { id: 'slide', name: 'Slide' },
    { id: 'zoom', name: 'Zoom' }
  ]

  useEffect(() => {
    loadProjects()
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl)
      }
    }
  }, [])

  const loadProjects = async () => {
    try {
      const response = await axios.get('http://localhost:8000/video/projects', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setProjects(response.data)
    } catch (error) {
      console.error('Error loading projects:', error)
    }
  }

  const handleFileUpload = (event) => {
    const file = event.target.files[0]
    if (file && file.type.startsWith('video/')) {
      setVideoFile(file)
      const url = URL.createObjectURL(file)
      setVideoUrl(url)

      // Create initial clip
      const clip = {
        id: Date.now(),
        file: file,
        start: 0,
        end: 0, // Will be set when video loads
        duration: 0,
        name: file.name
      }
      setClips([clip])
      setSelectedClip(clip.id)
    }
  }

  const handleVideoLoad = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
      setClips(prev => prev.map(clip =>
        clip.id === selectedClip
          ? { ...clip, end: videoRef.current.duration, duration: videoRef.current.duration }
          : clip
      ))
    }
  }

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
    }
  }

  const seekTo = (time) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time
      setCurrentTime(time)
    }
  }

  const addClip = () => {
    const newClip = {
      id: Date.now(),
      file: null,
      start: 0,
      end: 0,
      duration: 0,
      name: `Clip ${clips.length + 1}`
    }
    setClips(prev => [...prev, newClip])
    setSelectedClip(newClip.id)
  }

  const splitClip = () => {
    if (!selectedClip) return

    const clip = clips.find(c => c.id === selectedClip)
    if (!clip) return

    const splitTime = currentTime - clip.start
    const firstClip = {
      ...clip,
      id: Date.now(),
      end: clip.start + splitTime,
      duration: splitTime
    }

    const secondClip = {
      ...clip,
      id: Date.now() + 1,
      start: clip.start + splitTime,
      name: `${clip.name} (part 2)`
    }

    setClips(prev => prev
      .filter(c => c.id !== selectedClip)
      .concat([firstClip, secondClip])
      .sort((a, b) => a.start - b.start)
    )
    setSelectedClip(firstClip.id)
  }

  const applyEffect = async (effectType) => {
    setIsProcessing(true)
    try {
      const response = await axios.post('http://localhost:8000/video/apply-effect', {
        clipId: selectedClip,
        effect: effectType,
        timestamp: currentTime
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      setEffects(prev => [...prev, {
        id: Date.now(),
        clipId: selectedClip,
        type: effectType,
        startTime: currentTime,
        endTime: currentTime + 5 // 5 second effect
      }])

      alert('Effect applied successfully!')
    } catch (error) {
      alert('Error applying effect: ' + error.message)
    } finally {
      setIsProcessing(false)
    }
  }

  const generateWithAI = async () => {
    setIsProcessing(true)
    try {
      const response = await axios.post('http://localhost:8000/video/generate', {
        prompt: aiPrompt,
        duration: 10,
        style: 'cinematic'
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      // Add generated video clip
      const generatedClip = {
        id: Date.now(),
        file: null,
        start: duration,
        end: duration + 10,
        duration: 10,
        name: 'AI Generated Clip',
        aiGenerated: true
      }

      setClips(prev => [...prev, generatedClip])
      setDuration(prev => prev + 10)

      alert('AI video generated successfully!')
    } catch (error) {
      alert('Error generating video: ' + error.message)
    } finally {
      setIsProcessing(false)
    }
  }

  const exportVideo = async () => {
    setIsProcessing(true)
    try {
      const response = await axios.post('http://localhost:8000/video/export', {
        clips: clips,
        effects: effects,
        projectName: currentProject
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      // Download the exported video
      const link = document.createElement('a')
      link.href = response.data.downloadUrl
      link.download = `${currentProject}.mp4`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      alert('Video exported successfully!')
    } catch (error) {
      alert('Error exporting video: ' + error.message)
    } finally {
      setIsProcessing(false)
    }
  }

  const saveProject = async () => {
    try {
      await axios.post('http://localhost:8000/video/save', {
        name: currentProject,
        clips: clips,
        effects: effects
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      alert('Video project saved successfully!')
      loadProjects()
    } catch (error) {
      alert('Error saving project: ' + error.message)
    }
  }

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    const milliseconds = Math.floor((time % 1) * 100)
    return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(2, '0')}`
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{ padding: '1rem', borderBottom: '1px solid #ccc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <input
            type="text"
            value={currentProject}
            onChange={(e) => setCurrentProject(e.target.value)}
            placeholder="Project name"
            style={{ padding: '0.5rem' }}
          />
          <button onClick={saveProject} style={{ marginLeft: '1rem' }}>Save Project</button>
        </div>
        <div>
          <input
            type="file"
            accept="video/*"
            onChange={handleFileUpload}
            style={{ marginRight: '1rem' }}
          />
          <button onClick={exportVideo} disabled={isProcessing}>
            {isProcessing ? 'Processing...' : 'Export Video'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1 }}>
        {/* Video Preview */}
        <div style={{ flex: 1, padding: '1rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ position: 'relative', flex: 1, background: '#000', borderRadius: '8px', overflow: 'hidden' }}>
            {videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                onLoadedMetadata={handleVideoLoad}
                onTimeUpdate={handleTimeUpdate}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#666',
                fontSize: '1.2rem'
              }}>
                Upload a video to start editing
              </div>
            )}

            {/* Video Controls */}
            {videoUrl && (
              <div style={{
                position: 'absolute',
                bottom: '0',
                left: '0',
                right: '0',
                background: 'rgba(0,0,0,0.7)',
                padding: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem'
              }}>
                <button onClick={togglePlayPause}>
                  {isPlaying ? '⏸️' : '▶️'}
                </button>
                <span style={{ color: 'white', fontSize: '0.9rem' }}>
                  {formatTime(currentTime)} / {formatTime(duration)}
                </span>
                <input
                  type="range"
                  min="0"
                  max={duration}
                  value={currentTime}
                  onChange={(e) => seekTo(parseFloat(e.target.value))}
                  style={{ flex: 1 }}
                />
              </div>
            )}
          </div>

          {/* AI Generation */}
          <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '4px' }}>
            <h4>AI Video Generation</h4>
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="Describe the video scene you want to generate..."
              rows={2}
              style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem' }}
            />
            <button onClick={generateWithAI} disabled={isProcessing}>
              {isProcessing ? 'Generating...' : 'Generate with AI'}
            </button>
          </div>
        </div>

        {/* Timeline and Tools */}
        <div style={{ width: '400px', borderLeft: '1px solid #ccc', display: 'flex', flexDirection: 'column' }}>
          {/* Tools */}
          <div style={{ padding: '1rem', borderBottom: '1px solid #ccc' }}>
            <h4>Tools</h4>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <button onClick={addClip}>Add Clip</button>
              <button onClick={splitClip} disabled={!selectedClip}>Split</button>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label>Effect: </label>
              <select
                value={currentEffect}
                onChange={(e) => setCurrentEffect(e.target.value)}
                style={{ marginLeft: '0.5rem' }}
              >
                {effectTypes.map(effect => (
                  <option key={effect.id} value={effect.id}>
                    {effect.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => applyEffect(currentEffect)}
                disabled={!selectedClip || isProcessing}
                style={{ marginLeft: '0.5rem' }}
              >
                Apply
              </button>
            </div>
          </div>

          {/* Clips List */}
          <div style={{ padding: '1rem', borderBottom: '1px solid #ccc', flex: 1 }}>
            <h4>Clips ({clips.length})</h4>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {clips.map(clip => (
                <div
                  key={clip.id}
                  onClick={() => setSelectedClip(clip.id)}
                  style={{
                    padding: '0.5rem',
                    margin: '0.25rem 0',
                    background: selectedClip === clip.id ? '#e0e0e0' : '#f9f9f9',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontWeight: 'bold' }}>{clip.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#666' }}>
                    {formatTime(clip.start)} - {formatTime(clip.end)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline */}
          <div style={{ padding: '1rem', flex: 1 }}>
            <h4>Timeline</h4>
            <div
              ref={timelineRef}
              style={{
                height: '200px',
                background: '#f0f0f0',
                border: '1px solid #ccc',
                borderRadius: '4px',
                position: 'relative',
                overflowX: 'auto'
              }}
            >
              {/* Timeline ruler */}
              <div style={{
                height: '20px',
                background: '#e0e0e0',
                borderBottom: '1px solid #ccc',
                position: 'relative'
              }}>
                {Array.from({ length: Math.ceil(duration / 5) + 1 }, (_, i) => (
                  <div
                    key={i}
                    style={{
                      position: 'absolute',
                      left: `${(i * 5 / duration) * 100}%`,
                      top: '0',
                      bottom: '0',
                      width: '1px',
                      background: '#999'
                    }}
                  >
                    <span style={{
                      position: 'absolute',
                      top: '-18px',
                      left: '-10px',
                      fontSize: '0.7rem',
                      color: '#666'
                    }}>
                      {i * 5}s
                    </span>
                  </div>
                ))}
              </div>

              {/* Clips in timeline */}
              <div style={{ padding: '5px' }}>
                {clips.map(clip => (
                  <div
                    key={clip.id}
                    style={{
                      height: '40px',
                      background: selectedClip === clip.id ? '#4CAF50' : '#2196F3',
                      borderRadius: '4px',
                      position: 'absolute',
                      left: `${(clip.start / duration) * 100}%`,
                      width: `${(clip.duration / duration) * 100}%`,
                      top: '25px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0 0.5rem',
                      color: 'white',
                      fontSize: '0.8rem'
                    }}
                    onClick={() => setSelectedClip(clip.id)}
                  >
                    {clip.name}
                  </div>
                ))}

                {/* Playhead */}
                <div style={{
                  position: 'absolute',
                  left: `${(currentTime / duration) * 100}%`,
                  top: '0',
                  bottom: '0',
                  width: '2px',
                  background: 'red',
                  pointerEvents: 'none'
                }} />
              </div>
            </div>
          </div>

          {/* Projects */}
          <div style={{ padding: '1rem', borderTop: '1px solid #ccc' }}>
            <h4>Projects</h4>
            <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
              {projects.map(project => (
                <div key={project.id} style={{
                  padding: '0.5rem',
                  margin: '0.25rem 0',
                  background: '#f9f9f9',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}>
                  {project.name}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VideoEditor