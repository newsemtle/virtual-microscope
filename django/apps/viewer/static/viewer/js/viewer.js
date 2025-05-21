const slideMetadata = {
    mppX: parseFloat(rawSlideMetadata["mpp-x"]).toFixed(3), // toFixed(3)를 사용하여 소수점 3자리 문자열로 만들 수도 있음
    objectivePower: parseInt(rawSlideMetadata.objective_power, 10),
};

let currentMagnification;
let navShown = true;
let annotationEditMode = false;

let plugin;

// Openseadragon 초기화
const viewer = OpenSeadragon({
    id: "openseadragon-container",
    tileSources: API_ROUTES.slides.detail(slideId).dzi,
    prefixUrl: "/static/lib/openseadragon/images/",

    // 네비게이터
    showNavigator: true,
    navigatorPosition: "BOTTOM_RIGHT", // 네비게이터 위치
    navigatorSizeRatio: 0.17, // 네비게이터 크기를 뷰어의 얼마 비율로
    navigatorMaintainSizeRatio: true, // 뷰어 크기 변경되면 네비게이터도 바뀜
    navigatorDisplayRegionColor: "blue", // viewport 구역 표시 색
    navigatorBorderColor: "rgba(0, 0, 0, 0.4)", // 테두리 색색
    navigatorBackground: "rgb(248, 249, 250)", // 배경색
    navigatorAutoFade: false,

    // 네비게이션 컨트롤
    showNavigationControl: true,
    navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_RIGHT,
    zoomInButton: "zoom-in",
    zoomOutButton: "zoom-out",
    homeButton: "home",
    fullPageButton: "full-page",
    nextButton: "next",
    previousButton: "previous",
    maxZoomLevel: 52, //최대 줌 레벨 설정. 100X까지 되도록 설정함.
    // showRotationControl: true,
    gestureSettingsMouse: {
        clickToZoom: false, //사용시 약간 불편해서 꺼둠 (250210)
        dblClickToZoom: true,
        pinchToZoom: true,
        scrollToZoom: true,
        pinchRotate: true,
    },

    // Accessibility
    autoResize: true,
    preserveImageSizeOnResize: true,
    tabIndex: -1,
    IOSDevice: window.navigator.userAgent.match(/(iPad|iPhone|iPod)/g),
});

// Scalebar 추가
viewer.scalebar({
    type: OpenSeadragon.ScalebarType.MICROSCOPY,
    pixelsPerMeter: 1 / slideMetadata.mppX * 1000000,
    minWidth: "150px",
    location: OpenSeadragon.ScalebarLocation.BOTTOM_LEFT,
    color: "black",
    fontColor: "black",
    backgroundColor: "rgba(255, 255, 255, 0.5)",
    fontSize: "large",
    barThickness: 3,
});

// 최대 zoom level 설정
viewer.addHandler("open", function () {
    // 100배에 필요한 zoom factor를 미리 구해본 뒤 그 값을 maxZoomLevel에 설정
    viewer.viewport.maxZoomLevel = calculateZoomFactor(100);

    const contentFactor = viewer.world._contentFactor;

    // OSDMeasure 초기화
    plugin = new OSDMeasure(viewer, {
        conversionFactor: slideMetadata.mppX,
        units: "um",
        fontSize: contentFactor / 50,
        selectedColor: getAnnoColor(),
    });
});

// deselect measurement on click outside
viewer.addHandler("canvas-click", function (event) {
    const clickedElement = event.originalEvent.target;

    // Check if the clicked element is not part of a measurement
    if (!clickedElement.closest(".osd-measure-element")) {
        plugin.deselectMeasurement();
    }
});

// disable default keyboard shortcut
viewer.addHandler("canvas-key", function (event) {
    event.cancelEvent();
});

// viewer.addHandler('update-viewport', function () {
//     // Viewport Zoom 가져오기
//     var viewportZoom = viewer.viewport.getZoom();

//     // Viewport Zoom을 Image Zoom으로 변환
//     var imageZoom = viewer.viewport.viewportToImageZoom(viewportZoom);

//     // 콘솔에 출력
//     console.log("Viewport Zoom:", viewportZoom);
//     console.log("Image Zoom:", imageZoom);
// });

// Annotorious 초기화
const annoStyle = (annotation, state) => {
    const color = annotation.motivation;
    return {
        fillOpacity: 0,
        stroke: color,
        strokeOpacity: 1,
        strokeWidth: 3,
    };
};
let anno = AnnotoriousOSD.createOSDAnnotator(viewer, {style: annoStyle});
let anno2;
let activeAnno = anno;
if (!CAN_CREATE_ANNOTATION) {
    anno.setUserSelectAction("NONE");
    anno2 = AnnotoriousOSD.createOSDAnnotator(viewer, {style: annoStyle});
    activeAnno = anno2;
}
AnnotoriousTools.mountPlugin(activeAnno);  // support drawing ellipse

activeAnno.on("createAnnotation", (annotation) => {
    activeAnno.setDrawingEnabled(false);
    viewer.setMouseNavEnabled(true);
    annotation.motivation = getAnnoColor();

    annotationEditMode = false;
    openPopup(annotation);
});

//주석 선택 후 지우개 버튼 클릭하면 -> 지우기
activeAnno.on("selectionChanged", (annotation) => {
    let deleteBtn = document.getElementById("erase-btn");
    let editBtn = document.getElementById("edit-btn");

    if (annotation[0] != null) { //주석이 선택된 경우
        let selectedAnnotation = annotation[0]; // 현재 선택된 주석 저장
        // 기존 이벤트를 덮어쓰는 방식으로 클릭 이벤트 설정
        deleteBtn.onclick = () => {
            activeAnno.removeAnnotation(selectedAnnotation.id);

            // article-header와 article-body에서 해당 annotation의 요소 제거
            let bodyElem = document.getElementById("annotation-combined-" + selectedAnnotation.id);
            if (bodyElem) bodyElem.remove();

        };

        // 편집 버튼 클릭 이벤트 설정 - openEditPopup 함수 호출
        editBtn.onclick = () => {
            openEditPopup(selectedAnnotation);
        };

        document.getElementById("erase-btn").style.display = "block";
        document.getElementById("edit-btn").style.display = "block";

    } else { // 주석 선택이 해제된 경우
        // 클릭 이벤트 제거 (null로 설정)
        deleteBtn.onclick = null;
        document.getElementById("erase-btn").style.display = "none";
        document.getElementById("edit-btn").style.display = "none";
    }
});

//OSDMeasure 삭제 버튼 띄우기
window.addEventListener("measurement-selected", e => {
    const m = e.detail.measurement;

    // 원하는 정보 띄우기
    document.getElementById("erase-btn").style.display = "block";

    // 삭제 버튼에 해당 측정 저장
    document.getElementById("erase-btn").onclick = () => {
        plugin.deleteSelectedMeasurement(m);
        document.getElementById("erase-btn").style.display = "none";
    };
});

window.addEventListener("measurement-deselected", () => {
    document.getElementById("erase-btn").style.display = "none";
});

document.addEventListener("DOMContentLoaded", function () {

    //저장된 주석 이미지 및 설명(슬라이드 자체 설명 & 주석 설명) 띄우기 (fetch 사용 제거)
    if (annotation && annotation.data) {
        initializeAnnotation(annotation);
    }

    // 이미지 필터 초기화
    updateFilters();

    // 배율 추적 시작
    trackZoomAndUpdateButton();

    // 색상 선택
    document.querySelectorAll(".color-option").forEach(item => {
        item.addEventListener("click", (event) => {
            const selectedColor = item.dataset.color;
            setAnnoColor(selectedColor);
            plugin.setMeasurementColor(selectedColor);
        });
    });

    // .dropdown-item-text 클릭 시 드롭다운이 닫히지 않도록 방지
    document.querySelectorAll(".dropdown-item-text").forEach(item => {
        item.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    });

    // 주석 숨기기 버튼 클릭 이벤트 핸들러
    document.getElementById("invisible-btn").addEventListener("click", function () {
        const icon = this.querySelector("i");
        // 현재 아이콘이 eye-slash이면 보이는 상태 => 숨기기
        if (icon.classList.contains("bi-eye-slash")) {
            activeAnno.cancelSelected();
            activeAnno.setVisible(false); // 주석 숨기기
            icon.classList.remove("bi-eye-slash");
            icon.classList.add("bi-eye");
            this.title = "Show Annotation";

            plugin.deselectMeasurement();
            plugin.measurements.forEach(m => {
                if (m.line) m.line.visible = false;
                if (m.textObject) m.textObject.visible = false;
                if (m.p1?.fabricObject) m.p1.fabricObject.visible = false;
                if (m.p2?.fabricObject) m.p2.fabricObject.visible = false;
            });
            plugin.fabricCanvas.renderAll();
        } else {
            // 현재 아이콘이 eye이면 안 보이는 상태 => 보이기
            activeAnno.setVisible(true); // 주석 보이기
            icon.classList.remove("bi-eye");
            icon.classList.add("bi-eye-slash");
            this.title = "Hide Annotation";

            plugin.measurements.forEach(m => {
                if (m.line) m.line.visible = true;
                if (m.textObject) m.textObject.visible = true;
                if (m.p1?.fabricObject) m.p1.fabricObject.visible = true;
                if (m.p2?.fabricObject) m.p2.fabricObject.visible = true;
            });
            plugin.fabricCanvas.renderAll();
        }
    });

    // Add keyboard controls
    document.addEventListener("keydown", function (event) {
        const activeEl = document.activeElement;
        if (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA") {
            return; // 입력창에 포커스 있을 땐 키 막기
        }

        const key = event.key.toUpperCase();

        // Combination keys
        if (event.ctrlKey && key === "S") {
            event.preventDefault();
            captureOpenSeadragonView();
            return;
        } else if (event.ctrlKey && key === "C") {
            captureOpenSeadragonView(false);
            return;
        }

        // Single keys
        switch (key) {
            case "N":
                toggleNav(); //네비게이터 불러오기
                break;
            case "F":
                toggleFullScreen(); //전체화면
                break;
            case "H":
            case "0":
                viewer.viewport.goHome(true); //reset view
                break;
            // case "R":
            //     viewer.viewport.rotateBy(90); // 90도 회전 : 제대로 안됨. 보류
            //     break;

            //숫자키 입력시 배율 조정
            case "1":
                setZoomLevel(1.25);
                break;
            case "2":
                setZoomLevel(2.5);
                break;
            case "3":
                setZoomLevel(5);
                break;
            case "4":
                setZoomLevel(10);
                break;
            case "5":
                setZoomLevel(20);
                break;
            case "6":
                setZoomLevel(40);
                break;
            case "7":
                setZoomLevel(63);
                break;
            case "8":
                setZoomLevel(100);
                break;

            // 직사각형, 타원형 주석 지우기
            // case "BACKSPACE":   // 맥OS 이용자
            // case "DELETE":      // 윈도우 이용자
            //     let selectedAnno = anno.getSelected()[0];
            //     if (selectedAnno) {
            //         anno.removeAnnotation(selectedAnno.id);
            //     }
            //     break;
        }
    });

    // Add touch gesture support
    let touchStartX = 0;
    let touchStartY = 0;
    document.getElementById("openseadragon-container").addEventListener("touchstart", function (e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    });

    // change annotation
    const annotationDropdown = document.getElementById("annotation-change-dropdown");
    const dropdownToggle = annotationDropdown?.querySelector(".dropdown-toggle");
    const dropdownMenu = annotationDropdown?.querySelector(".dropdown-menu");
    dropdownToggle?.addEventListener("show.bs.dropdown", async function (event) {
        await drfRequest({
            url: API_ROUTES.slides.detail(slideId).annotations,
            onSuccess: (data) => {
                dropdownMenu.innerHTML = "";

                const listItem = document.createElement("li");
                dropdownMenu.appendChild(listItem);

                const button = document.createElement("button");
                button.classList.add("dropdown-item");
                button.innerHTML = `<i class="bi bi-image-fill"></i> (${gettext("None")})`;
                listItem.appendChild(button);

                data.forEach(annotation => {
                    const listItem = document.createElement("li");
                    dropdownMenu.appendChild(listItem);

                    const button = document.createElement("button");
                    button.classList.add("dropdown-item");
                    button.dataset.annotationId = annotation.id;
                    button.innerHTML = `<i class="bi bi-file-earmark-arrow-down"></i> ${annotation.name}`;
                    listItem.appendChild(button);
                });
            },
        });
        bootstrap.Dropdown.getOrCreateInstance(dropdownToggle)._popper?.update();
    });
    dropdownMenu?.addEventListener("click", function (event) {
        const button = event.target.closest("button");
        const annotationId = button.dataset.annotationId;
        loadAnnotation(annotationId);
    });

    // save: update annotation
    document.getElementById("annotation-update-btn")?.addEventListener("click", function (event) {
        const data = {
            description: decodeHTML(document.getElementById("slide-description").innerHTML),
            data: anno.getAnnotations(),
        };

        drfRequest({
            url: API_ROUTES.annotations.detail(annotation.id).base,
            method: "PATCH",
            data: data,
            onSuccess: (data) => {
                annotation.description = data.description;
                annotation.data = data.data;
                showFeedback(interpolate(gettext("Annotation '%(name)s' updated successfully!"), {name: data.name}, true), "success");
            },
            onError: (error) => {
                showFeedback(gettext("Failed to update annotation."), "danger");
            },
        });
    });

    // save: create annotation
    document.getElementById("annotation-create-form")?.addEventListener("submit", function (event) {
        event.preventDefault();

        const form = this;
        const formData = new FormData(this);

        const data = {
            name: formData.get("name"),
            slide: formData.get("slide"),
            description: decodeHTML(document.getElementById("slide-description").innerHTML),
            data: anno.getAnnotations(),
        };

        drfRequest({
            url: API_ROUTES.annotations.list.base,
            method: "POST",
            data: data,
            onSuccess: (data) => {
                bootstrap.Modal.getInstance(document.getElementById("annotation-create-modal")).hide();

                window.history.replaceState(null, "", window.location.pathname + `?annotation=${data.id}`);
                showFeedback(interpolate(gettext("Annotation '%(name)s' created successfully!"), {name: data.name}, true), "success");
                clearAnnotations();
                initializeAnnotation(data);
                annotation = data;
                document.getElementById("annotation-update-btn").disabled = !data.editable;
            },
            onError: (error) => {
                handleFormErrors(form, error);
            },
        });
    });

    // slide description input
    const description = document.getElementById("slide-description");
    const descriptionText = document.getElementById("description-text");
    document.getElementById("description-modal")?.addEventListener("show.bs.modal", function (event) {
        descriptionText.value = decodeHTML(description.innerHTML);
    });
    document.getElementById("apply-description")?.addEventListener("click", function (event) {
        description.innerHTML = encodeHTML(descriptionText.value);
    });

});

function initializeAnnotation(annotation) {
    document.getElementById("annotation-name").textContent = truncateString(annotation.name, 15);

    annotation.data.forEach(annot => {
        anno.addAnnotation(annot);
        updateAnnotationDisplay(annot);
    });

    //슬라이드 자체 설명
    const descriptionElement = document.getElementById("slide-description");
    descriptionElement.innerHTML = encodeHTML(annotation.description);
}

function clearAnnotations() {
    document.getElementById("annotation-name").textContent = `(${gettext("None")})`;
    anno.clearAnnotations();
    plugin.deselectMeasurement();
    plugin.clear();
    document.getElementById("slide-description").innerHTML = "";
    document.getElementById("article-body").innerHTML = "";
}

function loadAnnotation(annotationId = null) {
    if (annotationId === null) {
        window.history.replaceState(null, "", window.location.pathname);
        annotation = undefined;
        clearAnnotations();
        document.getElementById("annotation-update-btn").disabled = true;
        return;
    }
    drfRequest({
        url: API_ROUTES.annotations.detail(annotationId).base,
        onSuccess: (data) => {
            window.history.replaceState(null, "", window.location.pathname + `?annotation=${data.id}`);
            annotation = data;
            clearAnnotations();
            initializeAnnotation(data);
            document.getElementById("annotation-update-btn").disabled = !data.editable;
        },
    });
}

function toggleNav() {
    if (navShown) {
        viewer.navigator.element.style.display = "none";
    } else {
        viewer.navigator.element.style.display = "inline-block";
    }
    navShown = !navShown;
}

function toggleFullScreen() {
    if (!document.fullscreenElement) {
        document.getElementById("openseadragon-container").requestFullscreen()
            .catch(err => {
                console.log(`Error attempting to enable full-screen mode: ${err.message}`);
            });
    } else {
        document.exitFullscreen();
    }
}

function getAnnoColor() {
    return document.getElementById("ink").style.color;
}

function setAnnoColor(color) {
    document.getElementById("ink").style.color = color;
}

// Scale
//objectivePower의 값과 baseImageZoom을 이용하여 배율 보정정
function calculateZoomFactor(targetMagnification) {
    const objectivePower = slideMetadata.objectivePower;
    const baseImageZoom = viewer.viewport.viewportToImageZoom(objectivePower);
    return targetMagnification / baseImageZoom;
}

//zoom 설정정
function setZoomLevel(targetMagnification) {
    const zoomFactor = calculateZoomFactor(targetMagnification);
    viewer.viewport.zoomTo(zoomFactor, refPoint = null, immeadiately = true);
}

//현재 zoom을 추적, 버튼 업데이트 함수
function trackZoomAndUpdateButton() {
    const scaleButton = document.getElementById("btnGroupDrop_scale"); // Scale 버튼 선택
    if (!scaleButton) {
        console.error("Scale button not found");
        return;
    }

    //배율 변화 감지, 버튼에 반영
    viewer.addHandler("zoom", function () {
        let viewportZoom = viewer.viewport.getZoom();
        let imageZoom = viewer.viewport.viewportToImageZoom(viewportZoom);
        const objectivePower = slideMetadata.objectivePower;

        currentMagnification = imageZoom * objectivePower;

        const predefinedMagnifications = [5, 10, 20, 40, 63, 100]; // 정수 배율 리스트
        const buttonText = scaleButton.querySelector("span");
        if (predefinedMagnifications.includes(Math.round(currentMagnification))) {
            buttonText.textContent = `${Math.round(currentMagnification)}x`;
        } else {
            buttonText.textContent = `${currentMagnification.toFixed(2)}x`;
        }
    });
}

// 그리기 모드 변경 핸들러
function setDrawingTool(tool) {
    if (!activeAnno) return console.error("Annotorious is not initialized");
    activeAnno.setDrawingEnabled(true);
    activeAnno.setDrawingTool(tool);
    viewer.setMouseNavEnabled(false);
    //document.getElementById('openseadragon-viewer').classList.add('cursor-crosshair');
}

function openPopup(annotation) {
    return new Promise((resolve, reject) => {
        // 입력 필드 초기화
        document.getElementById("title").value = "";
        document.getElementById("comment").value = "";
        document.getElementById("overlay").style.display = "block";
        document.getElementById("annotation-popup").style.display = "block";

        const form = document.getElementById("annotation-form");

        // 팝업에서 제목과 코멘트 입력 후 저장할 때 실행
        form.addEventListener("submit", function (event) {
            event.preventDefault();

            const title = document.getElementById("title").value;
            const comment = document.getElementById("comment").value;

            annotation.name = title;
            annotation.description = comment;

            if (CAN_CREATE_ANNOTATION) {
                updateAnnotationDisplay(annotation);
            }

            closePopup();

            resolve(annotation);
        });
    });
}

// 팝업을 닫는 함수
function closePopup() {
    document.getElementById("overlay").style.display = "none";
    document.getElementById("annotation-popup").style.display = "none";
}

function cancelPopup() {
    if (!annotationEditMode) {
        activeAnno.removeAnnotation(activeAnno.getSelected()[0]);
    }
    closePopup();
}

function updateAnnotationDisplay(annotation) {
    // article-body에 주석의 설명과 이름을 한 문단으로 추가
    const articleBody = document.getElementById("article-body");
    const combinedElement = document.createElement("p");
    combinedElement.id = "annotation-combined-" + annotation.id;

    // 설명 부분
    const descriptionSpan = document.createElement("span");
    descriptionSpan.classList.add("annotation-description");
    descriptionSpan.style.color = "black";
    descriptionSpan.innerHTML = annotation.description.replace(/\n/g, "<br>");

    // 구분자
    const separator = document.createTextNode(": ");

    // 이름 부분
    const nameSpan = document.createElement("span");
    nameSpan.classList.add("annotation-name");
    nameSpan.style.color = "blue";
    nameSpan.innerHTML = annotation.name.replace(/\n/g, "<br>");

    // 요소들을 조합하여 하나의 문단에 추가
    combinedElement.appendChild(nameSpan);
    combinedElement.appendChild(separator);
    combinedElement.appendChild(descriptionSpan);

    articleBody.appendChild(combinedElement);

    // 클릭 시 주석 영역으로 이동 (combinedElement 전체에 이벤트 적용)
    combinedElement.addEventListener("click", function () {
        anno.fitBounds(annotation, {immediately: false, padding: 50});
    });
}

// 주석 수정 함수
function openEditPopup(annotation) {
    annotationEditMode = true;
    // 기존 값으로 입력 필드 미리 채우기
    document.getElementById("title").value = annotation.name || "";
    document.getElementById("comment").value = annotation.description || "";
    document.getElementById("overlay").style.display = "block";
    document.getElementById("annotation-popup").style.display = "block";

    const form = document.getElementById("annotation-form");

    form.onsubmit = function (event) {
        event.preventDefault();

        const newTitle = document.getElementById("title").value;
        const newComment = document.getElementById("comment").value;

        // 수정된 내용으로 annotation 업데이트
        annotation.name = newTitle;
        annotation.description = newComment;

        activeAnno.updateAnnotation(annotation);

        if (CAN_CREATE_ANNOTATION) {
            let bodyElem = document.getElementById("annotation-combined-" + annotation.id);
            if (bodyElem) bodyElem.remove();
            updateAnnotationDisplay(annotation);
        }

        closePopup();
    };
}

// Function to update filters based on slider values
function updateFilters() {
    const brightness = document.getElementById("brightness").value;
    const contrast = document.getElementById("contrast").value;
    const saturate = document.getElementById("saturate").value;

    // Update the displayed values
    document.getElementById("brightness-value").textContent = Math.round((parseFloat(brightness) * 100 - 100));
    document.getElementById("contrast-value").textContent = Math.round((parseFloat(contrast) * 100 - 100));
    document.getElementById("saturate-value").textContent = Math.round((parseFloat(saturate) * 100 - 100));

    // Apply CSS filters to the OpenSeadragon viewer
    document.querySelector("#openseadragon-container canvas").style.filter = `brightness(${brightness}) contrast(${contrast}) saturate(${saturate})`;
}

// Function to reset brightness to default
function resetBrightness() {
    const brightnessSlider = document.getElementById("brightness");
    brightnessSlider.value = 1;
    updateFilters();
}

// Function to reset contrast to default
function resetContrast() {
    const contrastSlider = document.getElementById("contrast");
    contrastSlider.value = 1;
    updateFilters();
}

function resetSaturate() {
    const saturateSlider = document.getElementById("saturate");
    saturateSlider.value = 1;
    updateFilters();
}

function getScreenshotFilename() {
    function getFormattedDate() {
        const d = new Date();
        const year = d.getFullYear().toString().padStart(4, "0");
        const month = (d.getMonth() + 1).toString().padStart(2, "0");
        const day = d.getDate().toString().padStart(2, "0");
        const hour = d.getHours().toString().padStart(2, "0");
        const minute = d.getMinutes().toString().padStart(2, "0");
        const second = d.getSeconds().toString().padStart(2, "0");
        return `${year}${month}${day}-${hour}${minute}${second}`;
    }

    const slideTitle = slideName.slice(0, 15).replace(/\s+/g, "_");
    const timeStr = getFormattedDate();
    return `${username}_${timeStr}_${slideTitle}`;
}

function captureOpenSeadragonView(saveToFile = true) {
    const canvas = document.querySelector("#openseadragon-container canvas");
    const filterValue = canvas.style.filter || "none";
    const ctx = canvas.getContext("2d");

    const originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    const tempCtx = tempCanvas.getContext("2d");
    tempCtx.filter = filterValue;
    tempCtx.drawImage(canvas, 0, 0);

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(tempCanvas, 0, 0);

    viewer.setMouseNavEnabled(false);
    viewer.setControlsEnabled(false);

    html2canvas(viewer.element, {
        useCORS: true,
        backgroundColor: null,
        scale: 2,
    }).then(originalCanvas => {
        const filename = getScreenshotFilename();
        const timestamp = formatDate(Date.now());

        // 여백 추가할 캔버스 만들기
        const marginHeight = 50; // 아래 여백 크기 (px)
        const finalCanvas = document.createElement("canvas");
        finalCanvas.width = originalCanvas.width;
        finalCanvas.height = originalCanvas.height + marginHeight;

        const finalCtx = finalCanvas.getContext("2d");

        // 전체 캔버스를 흰색으로 초기화
        finalCtx.fillStyle = "white";
        finalCtx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);

        // 원본 이미지 그리기
        finalCtx.drawImage(originalCanvas, 0, 0);

        // 텍스트 작성
        finalCtx.fillStyle = "black";
        finalCtx.font = "36px arial";
        finalCtx.textBaseline = "top";
        const slideTitle = slideName.slice(0, 30).replace(/\s+/g, "_");

        finalCtx.textAlign = "left";
        finalCtx.fillText(`${slideTitle}`, 10, originalCanvas.height + 5);
        finalCtx.textAlign = "center";
        finalCtx.fillText(`${gettext("Magnification")}: ${Math.round(currentMagnification)}x`, finalCanvas.width / 2, originalCanvas.height + 5);
        finalCtx.textAlign = "right";
        finalCtx.fillText(`${username} ${fullname} | ${timestamp}`, finalCanvas.width - 10, originalCanvas.height + 5);

        // 저장
        finalCanvas.toBlob(blob => {
            if (saveToFile) saveAs(blob, `${filename}.png`); // FileSaver

            const item = new ClipboardItem({"image/png": blob});
            navigator.clipboard.write([item])
                .then(() => {
                    showFeedback(gettext("Screenshot was copied to clipboard."), "success");
                })
                .catch(err => {
                    showFeedback(gettext("Failed to copy screenshot to clipboard."), "warning");
                });
        });

        // 복원
        ctx.putImageData(originalImageData, 0, 0);
        viewer.setMouseNavEnabled(true);
        viewer.setControlsEnabled(true);
    }).catch(err => {
        showFeedback(gettext("Failed to capture screenshot."), "danger");
        ctx.putImageData(originalImageData, 0, 0);
        viewer.setMouseNavEnabled(true);
        viewer.setControlsEnabled(true);
    });
}