// 서버에서 데이터를 비동기적으로 가져오는 함수
async function getServerData(request) {
    try {
        // 서버에 POST 요청을 보내고 응답을 기다림
        const response = await fetch('./api/serverData', {
            method: 'POST',
            body: JSON.stringify({ request }),
            headers: { 'Content-Type': 'application/json' }
        });

        // 응답 상태 확인
        if (!response.ok) {
            throw new Error(`HTTP 오류! 상태: ${response.status}`);
        }

        // 응답 데이터를 JSON으로 파싱하여 반환
        return await response.json();
    } catch (error) {
        console.error('서버 데이터 가져오기 오류:', error);
        throw error; // 오류를 상위로 전파
    }
}

// AG-Grid용 서버 사이드 데이터소스 생성 함수
function createServerSideDatasource() {
    return {
        // AG-Grid가 새 데이터를 요청할 때 호출되는 메서드
        getRows: async (params) => {
            try {
                console.log('요청 파라미터:', params);
                const result = await getServerData(params.request);
                console.log('데이터 결과:', result);

                // AG-Grid에 성공적으로 데이터 전달
                params.success(result.response);

                // 행 카운터 업데이트
                updateRowCounter(result.counter_info);
            } catch (error) {
                console.error('서버 데이터 가져오기 실패:', error);
                params.fail(); // AG-Grid에 실패 알림
            }
        }
    };
}

// 행 카운터 UI 업데이트 함수
function updateRowCounter(counterInfo) {
    const counterElement = document.getElementById("row-counter");
    if (counterElement) {
        counterElement.textContent = counterInfo;
    } else {
        console.warn("행 카운터 요소를 찾을 수 없습니다");
    }
}

// dash_ag_grid 라이브러리용 전역 함수 객체 초기화
window.dashAgGridFunctions = window.dashAgGridFunctions || {};

// 자식 요소 개수를 반환하는 함수
window.dashAgGridFunctions.getChildCount = function (data) {
    return data.childCount;
};

// 서버 사이드 데이터소스 생성 함수를 전역으로 노출
window.createServerSideDatasource = createServerSideDatasource;