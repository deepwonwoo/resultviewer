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














// Custom Header Component를 위한 네임스페이스 설정
var dagcomponentfuncs = window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};




// EditableHeaderComponent 정의
dagcomponentfuncs.EditableHeaderComponent = function(props) {
    // 컬럼 정보 및 디스플레이 이름 가져오기
    const { column, displayName, api, enableSorting, progressSort } = props;
    
    // 초기 editable 상태 확인
    const [isEditable, setIsEditable] = React.useState(column.getColDef().editable || false);
    
    // 정렬 상태 관리
    const [sortState, setSortState] = React.useState(column.getSort());
    
    // 컴포넌트 마운트 시 정렬 상태 확인
    React.useEffect(() => {
      setSortState(column.getSort());
      
      // 컬럼 정렬 상태 변경 이벤트 리스너 등록
      const onSortChanged = () => {
        setSortState(column.getSort());
      };
      
      column.addEventListener('sortChanged', onSortChanged);
      
      // 컴포넌트 언마운트 시 이벤트 리스너 제거
      return () => {
        column.removeEventListener('sortChanged', onSortChanged);
      };
    }, [column]);
    
    // editable 토글 핸들러
    const handleEditableToggle = (event) => {
      // 체크박스 상태 업데이트
      const newEditableState = event.target.checked;
      setIsEditable(newEditableState);
      
      // 컬럼 정의 업데이트
      const colDef = column.getColDef();
      colDef.editable = newEditableState;
      
      // 컬럼 스타일 클래스 업데이트
      if (newEditableState) {
        colDef.cellClass = "text-dark editable-column";
      } else {
        colDef.cellClass = "text-secondary";
      }
      
      // API를 통해 컬럼 정의 업데이트 및 그리드 리프레시
      api.setColumnDef(column.getColId(), colDef);
      api.refreshCells({ columns: [column.getColId()], force: true });
      
      // Dash 앱으로 데이터 전송 (cellRendererData prop 업데이트)
      if (api.dashGridOptions && typeof api.dashGridOptions.setCellRendererData === 'function') {
        api.dashGridOptions.setCellRendererData({
          action: 'toggle_editable',
          colId: column.getColId(),
          value: newEditableState,
          timestamp: new Date().getTime()
        });
      }
      
      // 이벤트 전파 방지
      event.stopPropagation();
    };
    
    // 정렬 핸들러 - 헤더 클릭 시 호출
    const onSortClicked = (event) => {
      if (enableSorting) {
        progressSort(event.shiftKey);
        // 정렬 상태 업데이트는 'sortChanged' 이벤트 리스너에서 처리됨
      }
      // 정렬 이벤트는 이벤트 버블링을 통해 그리드에 전달되어야 함
    };
    
    // 정렬 아이콘 렌더링 함수
    const renderSortIcon = () => {
      if (!enableSorting || !sortState) {
        return null;
      }
      
      // 정렬 아이콘 클래스 및 내용 결정
      let iconClass = '';
      let iconContent = '';
      
      if (sortState === 'asc') {
        iconClass = 'ag-sort-ascending-icon';
        iconContent = '▲'; // Unicode 상향 화살표
      } else if (sortState === 'desc') {
        iconClass = 'ag-sort-descending-icon';
        iconContent = '▼'; // Unicode 하향 화살표
      }
      
      // 정렬 아이콘이 없으면 null 반환
      if (!iconClass) {
        return null;
      }
      
      // 정렬 아이콘 스타일 정의
      const sortIconStyle = {
        marginLeft: '5px',
        fontSize: '10px',
        color: '#666'
      };
      
      // 정렬 아이콘 element 반환
      return React.createElement('span', {
        className: `ag-header-icon ag-header-label-icon ${iconClass}`,
        style: sortIconStyle
      }, iconContent);
    };
    
    // 헤더 스타일 정의
    const headerStyle = {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      width: '100%',
      padding: '0 5px',
      height: '100%',
      cursor: enableSorting ? 'pointer' : 'default'
    };
    
    // 헤더 텍스트 및 정렬 아이콘 컨테이너 스타일
    const headerTextContainerStyle = {
      display: 'flex',
      alignItems: 'center',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    };
    
    // 헤더 텍스트 스타일
    const headerTextStyle = {
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    };
    
    // 체크박스 컨테이너 스타일
    const checkboxContainerStyle = {
      display: 'flex',
      alignItems: 'center',
      marginLeft: '8px',
      flexShrink: 0
    };
    
    // 메인 컨테이너 렌더링
    return React.createElement(
      'div',
      { 
        style: headerStyle,
        onClick: onSortClicked,
        className: 'ag-header-cell-label'
      },
      [
        // 컬럼 이름 및 정렬 아이콘 컨테이너
        React.createElement(
          'div',
          { style: headerTextContainerStyle },
          [
            // 컬럼 이름
            React.createElement('span', {
              style: headerTextStyle,
              className: 'ag-header-cell-text'
            }, displayName),
            
            // 정렬 아이콘
            renderSortIcon()
          ]
        ),
        
        // 편집 가능 토글 체크박스 컨테이너
        React.createElement(
          'div',
          { 
            style: checkboxContainerStyle,
            onClick: (e) => e.stopPropagation() // 정렬 이벤트 방지
          },
          [
            // 체크박스 입력
            React.createElement('input', {
              type: 'checkbox',
              checked: isEditable,
              onChange: handleEditableToggle,
              style: { cursor: 'pointer' }
            }),
            
            // '편집' 텍스트
            React.createElement('span', { 
              style: { 
                fontSize: '10px', 
                marginLeft: '2px',
                color: isEditable ? '#2E64FE' : '#888'
              } 
            }, "Edit")
          ]
        )
      ]
    );
  };