import React, { useEffect, useRef, useState } from 'react';

export default function ShoulderModelViewer({ onRegionSelected, onClose }) {
  const iframeRef = useRef(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Dynamically load the Sketchfab Viewer API
    const script = document.createElement('script');
    script.src = 'https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js';
    script.async = true;
    script.onload = () => {
      initSketchfab();
    };
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  const initSketchfab = () => {
    const iframe = iframeRef.current;
    if (!iframe || !window.Sketchfab) return;

    const client = new window.Sketchfab(iframe);
    
    // The specific model ID provided by the user
    const uid = '94489e01f40548b5a0b4f0a6477c36a7';
    
    client.init(uid, {
      success: function onSuccess(api) {
        api.start();
        api.addEventListener('viewerready', function() {
          setLoading(false);
          
          // Pre-fetch node map and annotations
          let nodeMap = {};
          let annotations = [];
          
          api.getNodeMap(function(err, nodes) {
            if (!err) nodeMap = nodes;
          });

          api.getAnnotationList(function(err, list) {
            if (!err) annotations = list;
          });

          // Listen to clicks on the model
          api.addEventListener('click', function(info) {
            if (info && info.position3D) {
              const coords = info.position3D;
              let label = null;

              // 1. ANNOTATION "SNAP" (Highest Priority)
              // If a click is near a curated annotation (e.g. "Clavicle"), use that name.
              if (annotations && annotations.length > 0) {
                let closest = null;
                let minDist = 10.0; // Distance threshold (flexible depending on model scale)
                
                annotations.forEach(ann => {
                  if (ann.position) {
                    const dx = ann.position[0] - coords[0];
                    const dy = ann.position[1] - coords[1];
                    const dz = ann.position[2] - coords[2];
                    const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
                    
                    if (dist < minDist) {
                      minDist = dist;
                      closest = ann;
                    }
                  }
                });
                
                if (closest && closest.name) {
                  console.log("Annotation Snap Match:", closest.name, "Distance:", minDist);
                  label = closest.name;
                }
              }

              // 2. Core lookup (direct node -> nodeMap -> parents)
              const isMedical = (n) => n && n.length > 2 && !/mesh|geometry|mat_|material|default|object|grp|instance|node|body|cube|sphere|primitive/i.test(n);
              
              if (!label) {
                let rawName = info.node ? info.node.name : null;
                
                if (!isMedical(rawName) && info.instanceID && nodeMap) {
                  let node = Object.values(nodeMap).find(n => n.instanceID === info.instanceID);
                  let depth = 0;
                  while (node && !isMedical(node.name) && node.parentID && depth < 3) {
                    node = nodeMap[node.parentID];
                    depth++;
                  }
                  if (node && node.name) rawName = node.name;
                }

                // Fallback to material IF AND ONLY IF it's not "Mat" or "Material"
                if (!isMedical(rawName) && info.material && info.material.name && isMedical(info.material.name)) {
                  rawName = info.material.name;
                }
                
                label = rawName;
              }

              // Final Default
              if (!label || label.toLowerCase().includes('mat')) {
                label = `Shoulder Region`;
              }

              // Enhanced Cleanup Logic
              let cleaned = label
                .replace(/([A-Z])/g, ' $1') // CamelCase to spaces
                .replace(/_mesh|Mesh|Geometry|mat_|Material|default|object|grp|instance|node|body|[0-9_]/ig, ' ')
                .replace(/\s+/g, ' ')
                .trim();

              // COMPREHENSIVE SURGICAL MAPPING (Exhaustive Shoulder Anatomy)
              const anatomyDict = {
                'supraspinatus': 'Supraspinatus (Rotator Cuff)',
                'infraspinatus': 'Infraspinatus (Rotator Cuff)',
                'subscapularis': 'Subscapularis (Rotator Cuff)',
                'teres minor': 'Teres Minor (Rotator Cuff)',
                'rotator': 'Rotator Cuff',
                'deltoid': 'Deltoid Muscle',
                'pectoral': 'Pectoralis Major',
                'trapezius': 'Trapezius Muscle',
                'latissimus': 'Latissimus Dorsi',
                'teres major': 'Teres Major',
                'serratus': 'Serratus Anterior',
                'rhomboid': 'Rhomboid Muscle',
                'levator': 'Levator Scapulae',
                'bicep': 'Biceps Brachii',
                'tricep': 'Triceps Brachii',
                'clavicle': 'Clavicle (Collarbone)',
                'scapula': 'Scapula (Shoulder Blade)',
                'humerus': 'Humerus (Upper Arm Bone)',
                'acromion': 'Acromion Process',
                'coracoid': 'Coracoid Process',
                'glenoid': 'Glenoid Fossa',
                'ac joint': 'Aromioclavicular (AC) Joint',
                'gh joint': 'Shoulder Joint',
                'labrum': 'Glenoid Labrum',
                'bursa': 'Subacromial Bursa',
                'ligament': 'Shoulder Ligament',
                'tendon': 'Anatomical Tendon'
              };

              let mappedLabel = null;
              const lowerCleaned = cleaned.toLowerCase();
              for (const [key, val] of Object.entries(anatomyDict)) {
                if (lowerCleaned.includes(key)) {
                  mappedLabel = val;
                  break;
                }
              }

              let finalLabel = mappedLabel || (cleaned.length > 2 ? cleaned : "Shoulder Region");
              
              if (!mappedLabel && finalLabel !== "Shoulder Region") {
                finalLabel = finalLabel.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
              }

              console.log("Interactive Diagnosis:", { raw: label, cleaned, final: finalLabel });
              onRegionSelected(finalLabel, coords);
            }
          });
        });
      },
      error: function onError() {
        console.error('Sketchfab API error');
        setLoading(false);
      },
      ui_controls: 1,
      ui_infos: 0,
      ui_watermark: 0,
      ui_stop: 0,
      ui_annotations: 0,
      autostart: 1,
      camera: 0
    });
  };

  return (
    <div className="fade-in" style={{ 
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
      background: 'rgba(0,0,0,0.85)', zIndex: 100, 
      display: 'flex', alignItems: 'center', justifyContent: 'center', 
      backdropFilter: 'blur(8px)' 
    }}>
      <div style={{ 
        position: 'relative', width: '90%', maxWidth: '900px', height: '80vh', 
        background: '#0d1117', borderRadius: '24px', border: '1px solid #1e293b', 
        overflow: 'hidden', boxShadow: '0 25px 50px rgba(0,0,0,0.7)' 
      }}>
        
        {/* Header overlay allowing clicks to pass through except for the close button */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', zIndex: 10, background: 'linear-gradient(to bottom, rgba(13,17,23,0.95), transparent)', pointerEvents: 'none' }}>
          <div>
            <h3 style={{ color: 'white', margin: 0, fontSize: '18px', fontWeight: 600 }}>Specify Pain Location</h3>
            <p style={{ color: '#94a3b8', margin: '4px 0 0', fontSize: '13px' }}>Rotate and click explicitly on the 3D anatomical model.</p>
          </div>
          <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: 'white', cursor: 'pointer', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', transition: 'background 0.2s', pointerEvents: 'auto' }} onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'} onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}>
            ✕
          </button>
        </div>

        {loading && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'white', zIndex: 5, fontSize: '15px' }}>
            Loading High-Fidelity Anatomical Model...
          </div>
        )}

        {/* The Sketchfab embedded iframe */}
        <iframe 
          ref={iframeRef}
          title="Shoulder Joint" 
          frameBorder="0" 
          allowFullScreen 
          mozallowfullscreen="true" 
          webkitallowfullscreen="true" 
          allow="autoplay; fullscreen; xr-spatial-tracking" 
          xr-spatial-tracking="true" 
          execution-while-out-of-viewport="true" 
          execution-while-not-rendered="true" 
          web-share="true" 
          src="about:blank"
          style={{ width: '100%', height: '100%', border: 'none', background: '#0d1117' }}
        />
      </div>
    </div>
  );
}
