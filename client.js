let localStream = null;
let pc = null;

// Start button handler
document.getElementById('startButton').addEventListener('click', async () => {
    const localVideo = document.getElementById('localVideo');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('getUserMedia is not supported!');
        return;
    } else {
        localStream = await navigator.mediaDevices.getUserMedia({video: true});
        localVideo.srcObject = localStream;
    }
});

// Call button handler
document.getElementById('callButton').addEventListener('click', async () => {
    const remoteVideo = document.getElementById('remoteVideo');

    pc = new RTCPeerConnection();
    pc.ontrack = event => {
        remoteVideo.srcObject = event.streams[0];
    };

    localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
    });

    try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch('/offer', {
            method: 'POST',
            cache: 'no-cache',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({sdp: pc.localDescription.sdp, type: pc.localDescription.type})
        });

        const answer = await response.json();
        await pc.setRemoteDescription(answer);
    } catch (err) {
        console.error(err);
    }
});
